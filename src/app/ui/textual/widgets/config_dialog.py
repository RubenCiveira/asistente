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
from textual.widgets import Button, Static, Tree

from .form import SchemaForm


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

# FIXME: if apply => clear form pending 
# FIXME: if change page and form isPending => confirm.
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
        self._current_page: Optional[ConfigPage] = None
        self._form: Optional[SchemaForm] = None

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

        stored = self._page_values.get(page.id, {})
        self._form = SchemaForm(
            page.schema,
            initial_values=stored,
            id_prefix=f"cfg-{page.id}",
        )
        container.mount(self._form)

    # ------------------------------------------------------------------
    # Reading field values
    # ------------------------------------------------------------------

    def _save_current_values(self) -> None:
        """Read all widget values for the current page into the store."""
        if self._current_page is None:
            return
        page = self._current_page
        if self._form is None:
            return
        self._page_values[page.id] = self._form.get_values()

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
        if self._form is None:
            return
        error = self._form.handle_array_add(button_id)
        if error:
            self.query_one("#config-errors", Static).update(error)
            return
        self.query_one("#config-errors", Static).update("")

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
