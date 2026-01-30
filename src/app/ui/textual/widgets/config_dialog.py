"""Generic hierarchical configuration dialog.

This module provides :class:`ConfigDialog`, a :class:`~textual.screen.ModalScreen`
that presents a page tree on the right and a dynamic JSON-Schema-driven form on
the left.  Each page in the tree corresponds to a JSON Schema whose fields are
rendered simultaneously in a scrollable area.

Data model
----------
* :class:`ConfigPage` — a single page definition (id, title, schema, children).
* :class:`ConfigValues` — per-page values container (``values`` dict +
  ``childs`` dict mirroring the page hierarchy).

The dialog receives a list of top-level pages and an optional initial-values
dictionary keyed by page id.  On *Accept* it returns the updated values
dictionary.  On *Apply* it posts a :class:`ConfigDialog.Applied` message
without closing.

Usage example::

    pages = [
        ConfigPage(
            id="general",
            title="General",
            schema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["en", "es"]},
                },
            },
            children=[
                ConfigPage(
                    id="editor",
                    title="Editor",
                    schema={
                        "type": "object",
                        "properties": {
                            "font_size": {"type": "integer", "minimum": 8},
                        },
                    },
                ),
            ],
        ),
    ]
    initial = {
        "general": ConfigValues(
            values={"language": "en"},
            childs={
                "editor": ConfigValues(values={"font_size": 14}),
            },
        ),
    }
    result = await app.push_screen_wait(ConfigDialog(pages, initial))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator, validate, ValidationError
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    ListItem,
    ListView,
    RadioButton,
    RadioSet,
    SelectionList,
    Static,
    Tree,
)


@dataclass
class ConfigPage:
    """A single page in the configuration hierarchy.

    Parameters
    ----------
    id:
        Unique identifier for this page.
    title:
        Human-readable title shown in the navigation tree.
    schema:
        JSON Schema (Draft 2020-12) ``object`` definition for this page's
        form fields.
    children:
        Optional list of child pages forming a sub-tree.
    """

    id: str
    title: str
    schema: Dict[str, Any]
    children: Optional[List["ConfigPage"]] = field(default_factory=list)


@dataclass
class ConfigValues:
    """Per-page values container.

    Parameters
    ----------
    values:
        Mapping of field name to its current value.
    childs:
        Mapping of child page id to its :class:`ConfigValues`.
    """

    values: Dict[str, Any] = field(default_factory=dict)
    childs: Dict[str, "ConfigValues"] = field(default_factory=dict)


class ConfigDialog(ModalScreen[Optional[Dict[str, ConfigValues]]]):
    """Modal configuration dialog with a page tree and dynamic forms.

    The dialog shows a navigation tree on the right and a scrollable form
    area on the left.  Selecting a page in the tree renders all its fields
    at once.  Three action buttons are provided:

    * **Cancel** — dismiss with ``None``.
    * **Apply** — post an :class:`Applied` message with the current values;
      the dialog stays open.
    * **Accept** — dismiss with the collected values dictionary.

    Parameters
    ----------
    pages:
        Top-level configuration pages.  Each page may have children forming
        a tree.
    initial_values:
        Optional dictionary keyed by page id with :class:`ConfigValues`
        instances used to pre-populate form fields.
    title:
        Dialog title shown at the top.

    Returns
    -------
    Optional[Dict[str, ConfigValues]]
        The collected configuration on success, or ``None`` on cancel.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    ConfigDialog {
        align: center middle;
        background: $surface 80%;
    }

    #config-dialog {
        width: 90%;
        height: 80%;
        border: round $primary;
        background: $panel;
        padding: 1 2;
    }

    #config-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #config-body {
        height: 1fr;
    }

    #config-form-area {
        width: 2fr;
        padding-right: 1;
    }

    #config-tree {
        width: 1fr;
        border-left: solid $primary;
        padding-left: 1;
    }

    #config-errors {
        color: red;
        height: auto;
        margin-top: 1;
    }

    #config-buttons {
        height: auto;
        margin-top: 1;
        align: right middle;
    }

    .config-field-label {
        margin-top: 1;
        text-style: bold;
    }

    .config-field-label:first-child {
        margin-top: 0;
    }

    .config-array-items {
        height: auto;
        max-height: 8;
    }

    .config-array-row {
        height: auto;
    }

    .config-array-row Input {
        width: 1fr;
    }

    .config-array-row Button {
        width: auto;
    }
    """

    class Applied(Message):
        """Posted when the user clicks *Apply*.

        Attributes
        ----------
        values:
            The current configuration values dictionary.
        """

        def __init__(self, values: Dict[str, ConfigValues]) -> None:
            super().__init__()
            self.values = values

    def __init__(
        self,
        pages: List[ConfigPage],
        initial_values: Optional[Dict[str, ConfigValues]] = None,
        title: str = "Configuration",
    ) -> None:
        super().__init__()
        self._pages = pages
        self._title = title
        self._initial_values: Dict[str, ConfigValues] = dict(initial_values or {})

        # Flat store: page_id -> {field: value}
        self._page_values: Dict[str, Dict[str, Any]] = {}
        # Index: page_id -> ConfigPage
        self._page_index: Dict[str, ConfigPage] = {}
        # Parent mapping: page_id -> parent_page_id (None for roots)
        self._parent_map: Dict[str, Optional[str]] = {}
        # Track per-page array backing lists: page_id -> {field: [values]}
        self._array_stores: Dict[str, Dict[str, List[Any]]] = {}

        self._current_page: Optional[ConfigPage] = None

        self._index_pages(self._pages, None)
        self._load_initial_values()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _index_pages(
        self, pages: List[ConfigPage], parent_id: Optional[str]
    ) -> None:
        """Build the flat page index and parent map recursively."""
        for page in pages:
            self._page_index[page.id] = page
            self._parent_map[page.id] = parent_id
            if page.children:
                self._index_pages(page.children, page.id)

    def _load_initial_values(self) -> None:
        """Populate ``_page_values`` from the hierarchical initial values."""
        self._walk_initial(self._pages, self._initial_values)

    def _walk_initial(
        self,
        pages: List[ConfigPage],
        values: Dict[str, ConfigValues],
    ) -> None:
        for page in pages:
            cv = values.get(page.id)
            if cv is not None:
                self._page_values[page.id] = dict(cv.values)
            if page.children and cv is not None:
                self._walk_initial(page.children, cv.childs)

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Build the static widget tree."""
        with Vertical(id="config-dialog"):
            yield Static(self._title, id="config-title")
            with Horizontal(id="config-body"):
                yield VerticalScroll(id="config-form-area")
                yield Tree("Pages", id="config-tree")
            yield Static("", id="config-errors")
            with Horizontal(id="config-buttons"):
                yield Button("Cancel", id="cancel", variant="error")
                yield Button("Apply", id="apply", variant="warning")
                yield Button("Accept", id="accept", variant="primary")

    def on_mount(self) -> None:
        """Build the tree and select the first page."""
        self._build_tree()
        if self._pages:
            self._current_page = self._pages[0]
            self._render_page_form(self._current_page)
            # Select the first tree node
            tree = self.query_one("#config-tree", Tree)
            if tree.root.children:
                tree.select_node(tree.root.children[0])

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    def _build_tree(self) -> None:
        """Populate the Tree widget from the page hierarchy."""
        tree = self.query_one("#config-tree", Tree)
        tree.root.expand()
        tree.show_root = False
        for page in self._pages:
            node = tree.root.add(page.title, data=page)
            node.expand()
            if page.children:
                self._add_tree_children(node, page.children)

    def _add_tree_children(self, parent_node, children: List[ConfigPage]) -> None:
        for child in children:
            node = parent_node.add(child.title, data=child)
            node.expand()
            if child.children:
                self._add_tree_children(node, child.children)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Switch form to the selected page."""
        page = event.node.data
        if page is None or page == self._current_page:
            return
        self._save_current_values()
        self._current_page = page
        self._render_page_form(page)

    # ------------------------------------------------------------------
    # Form rendering — all fields at once
    # ------------------------------------------------------------------

    def _render_page_form(self, page: ConfigPage) -> None:
        """Clear and re-render the form area for *page*."""
        container = self.query_one("#config-form-area", VerticalScroll)
        container.remove_children()
        self.query_one("#config-errors", Static).update("")

        properties = page.schema.get("properties", {})
        required = set(page.schema.get("required", []))
        stored = self._page_values.get(page.id, {})

        # Initialise array stores for this page
        if page.id not in self._array_stores:
            self._array_stores[page.id] = {}

        for name, spec in properties.items():
            value = stored.get(name, spec.get("default"))
            self._mount_field(container, page.id, name, spec, name in required, value)

    def _mount_field(
        self,
        container: VerticalScroll,
        page_id: str,
        name: str,
        spec: Dict[str, Any],
        required: bool,
        value: Any,
    ) -> None:
        """Mount a single field (label + widget) into *container*."""
        label_text = name
        if spec.get("description"):
            label_text += f" -- {spec['description']}"
        if spec.get("default") is not None and value is None:
            label_text += f" [default: {spec['default']}]"
        if required:
            label_text += " *"

        widget_id = f"cfg-{page_id}-{name}"

        if "oneOf" in spec:
            buttons = [
                RadioButton(
                    opt.get("title", str(opt["const"])),
                    id=f"{widget_id}--{opt['const']}",
                )
                for opt in spec["oneOf"]
            ]
            rs = RadioSet(*buttons, id=widget_id)
            if value is not None:
                for rb in rs.query(RadioButton):
                    if rb.id == f"{widget_id}--{value}":
                        rb.value = True
                        break
            container.mount(Static(label_text, classes="config-field-label"), rs)

        elif "enum" in spec:
            buttons = [
                RadioButton(str(opt), id=f"{widget_id}--{opt}")
                for opt in spec["enum"]
            ]
            rs = RadioSet(*buttons, id=widget_id)
            if value is not None:
                for rb in rs.query(RadioButton):
                    if rb.id == f"{widget_id}--{value}":
                        rb.value = True
                        break
            container.mount(Static(label_text, classes="config-field-label"), rs)

        elif spec.get("type") == "boolean":
            cb = Checkbox(label_text, id=widget_id)
            if value is not None:
                cb.value = bool(value)
            container.mount(cb)

        elif spec.get("type") == "array":
            items_spec = spec.get("items", {})
            if "oneOf" in items_spec or "enum" in items_spec:
                options: list = []
                if "oneOf" in items_spec:
                    for opt in items_spec["oneOf"]:
                        val = opt.get("const")
                        title = opt.get("title", str(val))
                        options.append((title, str(val)))
                else:
                    for opt in items_spec["enum"]:
                        options.append((str(opt), str(opt)))
                sl: SelectionList[str] = SelectionList[str](
                    *options, id=widget_id
                )
                for v in value or []:
                    sl.select(str(v))
                container.mount(
                    Static(label_text, classes="config-field-label"), sl
                )
            else:
                # Free-text array
                arr = list(value or [])
                self._array_stores.setdefault(page_id, {})[name] = arr
                lv = ListView(
                    *[ListItem(Label(str(v))) for v in arr],
                    id=widget_id,
                    classes="config-array-items",
                )
                inp = Input(
                    placeholder="Add item and press Enter",
                    id=f"{widget_id}--input",
                )
                container.mount(
                    Static(label_text, classes="config-field-label"),
                    lv,
                    Horizontal(
                        inp,
                        Button("Add", id=f"{widget_id}--add"),
                        classes="config-array-row",
                    ),
                )

        else:
            inp = Input(placeholder=label_text, id=widget_id)
            if value is not None:
                inp.value = str(value)
            container.mount(Static(label_text, classes="config-field-label"), inp)

    # ------------------------------------------------------------------
    # Reading field values
    # ------------------------------------------------------------------

    def _save_current_values(self) -> None:
        """Read all widget values for the current page into the store."""
        if self._current_page is None:
            return
        page = self._current_page
        properties = page.schema.get("properties", {})
        values: Dict[str, Any] = {}
        for name, spec in properties.items():
            val = self._read_field_value(page.id, name, spec)
            if val is not None:
                values[name] = val
        self._page_values[page.id] = values

    def _read_field_value(
        self, page_id: str, name: str, spec: Dict[str, Any]
    ) -> Any:
        """Read the value from a single field widget."""
        widget_id = f"cfg-{page_id}-{name}"
        try:
            w = self.query_one(f"#{widget_id}")
        except Exception:
            return None

        if isinstance(w, SelectionList):
            return list(w.selected)

        if isinstance(w, RadioSet):
            prefix = f"{widget_id}--"
            for btn in w.query(RadioButton):
                if btn.value and btn.id and btn.id.startswith(prefix):
                    raw = btn.id[len(prefix):]
                    return self._cast_value(raw, spec.get("type", "string"))
            return None

        if isinstance(w, Checkbox):
            return w.value

        if isinstance(w, Input):
            raw = w.value.strip()
            if not raw:
                return None
            return self._cast_value(raw, spec.get("type", "string"))

        if isinstance(w, ListView):
            # Free-text array — values kept in _array_stores
            arr = self._array_stores.get(page_id, {}).get(name, [])
            return list(arr)

        return None

    # ------------------------------------------------------------------
    # Array helpers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses."""
        bid = event.button.id or ""
        if bid == "cancel":
            self.action_cancel()
        elif bid == "apply":
            self._apply()
        elif bid == "accept":
            self._accept()
        elif bid.endswith("--add"):
            self._handle_array_add(bid)

    def _handle_array_add(self, button_id: str) -> None:
        """Add item to a free-text array field."""
        # button_id = "cfg-<page_id>-<field>--add"
        base_id = button_id.removesuffix("--add")
        input_id = f"{base_id}--input"
        try:
            inp = self.query_one(f"#{input_id}", Input)
            lv = self.query_one(f"#{base_id}", ListView)
        except Exception:
            return

        raw = inp.value.strip()
        if not raw:
            return

        # Extract page_id and field name from base_id
        # base_id = "cfg-<page_id>-<field>"
        parts = base_id.split("-", 2)
        if len(parts) < 3:
            return
        page_id = parts[1]
        field_name = parts[2]

        page = self._page_index.get(page_id)
        if page is None:
            return
        spec = page.schema.get("properties", {}).get(field_name, {})
        items_spec = spec.get("items", {})
        item_type = items_spec.get("type", "string")

        try:
            value = self._cast_value(raw, item_type)
        except ValueError as e:
            self.query_one("#config-errors", Static).update(str(e))
            return

        # Validate item
        v = Draft202012Validator(items_spec)
        item_errors = [e.message for e in v.iter_errors(value)]
        if item_errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in item_errors)
            )
            return

        arr = self._array_stores.setdefault(page_id, {}).setdefault(
            field_name, []
        )

        if spec.get("uniqueItems", False) and value in arr:
            self.query_one("#config-errors", Static).update(
                "Duplicate value not allowed"
            )
            return

        arr.append(value)
        self.query_one("#config-errors", Static).update("")
        inp.value = ""
        lv.append(ListItem(Label(str(value))))
        inp.focus()

    # ------------------------------------------------------------------
    # Collecting / reconstructing values
    # ------------------------------------------------------------------

    def _collect_all_values(self) -> Dict[str, ConfigValues]:
        """Reconstruct the hierarchical values dict from the flat store."""
        self._save_current_values()
        return self._build_values(self._pages)

    def _build_values(
        self, pages: List[ConfigPage]
    ) -> Dict[str, ConfigValues]:
        result: Dict[str, ConfigValues] = {}
        for page in pages:
            child_vals: Dict[str, ConfigValues] = {}
            if page.children:
                child_vals = self._build_values(page.children)
            result[page.id] = ConfigValues(
                values=dict(self._page_values.get(page.id, {})),
                childs=child_vals,
            )
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_all(self) -> List[str]:
        """Validate every page against its schema.

        Returns a list of human-readable error strings.  Empty when valid.
        """
        self._save_current_values()
        errors: List[str] = []
        for page_id, page in self._page_index.items():
            data = self._page_values.get(page_id, {})
            try:
                validate(data, page.schema)
            except ValidationError as e:
                errors.append(f"{page.title}: {e.message}")
        return errors

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cancel(self) -> None:
        """Dismiss the dialog without saving."""
        self.dismiss(None)

    def _apply(self) -> None:
        """Validate and post an :class:`Applied` message."""
        errors = self._validate_all()
        if errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in errors)
            )
            return
        self.query_one("#config-errors", Static).update("")
        values = self._collect_all_values()
        self.post_message(self.Applied(values))

    def _accept(self) -> None:
        """Validate and dismiss with the collected values."""
        errors = self._validate_all()
        if errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in errors)
            )
            return
        values = self._collect_all_values()
        self.dismiss(values)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cast_value(raw: str, field_type: str) -> Any:
        """Convert *raw* string to the Python type implied by *field_type*.

        Parameters
        ----------
        raw:
            The non-empty string entered by the user.
        field_type:
            One of ``"string"``, ``"integer"``, ``"number"`` or
            ``"boolean"``.

        Returns
        -------
        str | int | float | bool

        Raises
        ------
        ValueError
            If conversion fails or the type is unsupported.
        """
        if field_type == "string":
            return raw
        if field_type == "integer":
            return int(raw)
        if field_type == "number":
            return float(raw)
        if field_type == "boolean":
            if raw.lower() in ("true", "yes", "y", "1"):
                return True
            if raw.lower() in ("false", "no", "n", "0"):
                return False
            raise ValueError("Expected boolean (yes/no, true/false)")
        raise ValueError(f"Unsupported type {field_type}")
