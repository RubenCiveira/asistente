"""Textual modal form dialog driven by JSON Schema.

This module provides :class:`FormDialog`, a :class:`~textual.screen.ModalScreen`
that renders a wizard-style form whose fields are derived from a JSON Schema
(Draft 2020-12).  Each property in the schema becomes one step of the wizard.
The dialog validates each field incrementally before advancing, and performs a
full-schema validation before returning the final result.

Supported field types
---------------------
* **string / integer / number** — rendered as :class:`~textual.widgets.Input`.
* **boolean** — rendered as :class:`~textual.widgets.Checkbox`.
* **enum** / **oneOf** — rendered as :class:`~textual.widgets.RadioSet`.
* **array with enum/oneOf items** — rendered as
  :class:`~textual.widgets.SelectionList` (multi-select).
* **array with free-text items** — rendered as a
  :class:`~textual.widgets.ListView` + :class:`~textual.widgets.Input`
  combination.  Users can navigate items with the arrow keys and remove
  a highlighted item by pressing backspace when the input is empty.

Usage example::

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "minimum": 1},
        },
        "required": ["name"],
    }
    result = await app.push_screen_wait(FormDialog(schema))
"""

from typing import Any, Dict, List, Optional
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Static,
    Checkbox,
    RadioSet,
    RadioButton,
    SelectionList,
    ListView,
    ListItem,
    Label,
)
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from jsonschema import Draft202012Validator, validate, ValidationError


class FieldRender:
    """Render a single JSON-Schema field into a container."""

    def __init__(
        self,
        container,
        *,
        id_prefix: Optional[str] = None,
        label_class: Optional[str] = None,
        include_input_label: bool = True,
        selection_list_id: Optional[str] = None,
        array_list_id: Optional[str] = None,
        array_input_id: Optional[str] = None,
        array_add_id: Optional[str] = None,
        array_row_id: Optional[str] = None,
        array_items_class: Optional[str] = None,
        array_row_class: Optional[str] = None,
    ) -> None:
        self._container = container
        self._id_prefix = id_prefix
        self._label_class = label_class
        self._include_input_label = include_input_label
        self._selection_list_id = selection_list_id
        self._array_list_id = array_list_id
        self._array_input_id = array_input_id
        self._array_add_id = array_add_id
        self._array_row_id = array_row_id
        self._array_items_class = array_items_class
        self._array_row_class = array_row_class

    def render(
        self,
        name: str,
        spec: Dict[str, Any],
        required: bool,
        value: Any,
    ) -> tuple[Optional[Widget], Optional[List[Any]]]:
        label = self._build_label(name, spec, required)
        widget_id = f"{self._id_prefix}-{name}" if self._id_prefix else None

        if "oneOf" in spec:
            buttons = []
            for opt in spec["oneOf"]:
                title = opt.get("title", opt.get("const"))
                const = opt.get("const")
                if widget_id:
                    button_id = f"{widget_id}--{const}"
                else:
                    button_id = str(const)
                buttons.append(RadioButton(title, id=button_id))
            rs = RadioSet(*buttons, id=widget_id)
            if value is not None:
                selected_id = (
                    f"{widget_id}--{value}" if widget_id else str(value)
                )
                for rb in rs.query(RadioButton):
                    if rb.id == selected_id:
                        rb.value = True
                        break
            self._container.mount(self._label_widget(label), rs)
            return rs, None

        if "enum" in spec:
            buttons = []
            for opt in spec["enum"]:
                if widget_id:
                    button_id = f"{widget_id}--{opt}"
                else:
                    button_id = str(opt)
                buttons.append(RadioButton(str(opt), id=button_id))
            rs = RadioSet(*buttons, id=widget_id)
            if value is not None:
                selected_id = (
                    f"{widget_id}--{value}" if widget_id else str(value)
                )
                for rb in rs.query(RadioButton):
                    if rb.id == selected_id:
                        rb.value = True
                        break
            self._container.mount(self._label_widget(label), rs)
            return rs, None

        if spec.get("type") == "boolean":
            cb = Checkbox(label, id=widget_id)
            if value is not None:
                cb.value = bool(value)
            self._container.mount(cb)
            return cb, None

        if spec.get("type") == "array":
            items_spec = spec.get("items", {})
            if "oneOf" in items_spec or "enum" in items_spec:
                options = []
                if "oneOf" in items_spec:
                    for opt in items_spec["oneOf"]:
                        val = opt.get("const")
                        title = opt.get("title", str(val))
                        options.append((title, str(val)))
                else:
                    for opt in items_spec["enum"]:
                        options.append((str(opt), str(opt)))

                sl_id = self._selection_list_id or widget_id
                sl = SelectionList[str](*options, id=sl_id)
                for v in value or []:
                    sl.select(str(v))
                self._container.mount(self._label_widget(label), sl)
                return sl, None

            array_values = list(value or [])
            lv_id = self._array_list_id or widget_id
            lv = ListView(
                *[ListItem(Label(str(v))) for v in array_values],
                id=lv_id,
                classes=self._array_items_class,
            )
            input_id = self._array_input_id
            if input_id is None and widget_id:
                input_id = f"{widget_id}--input"
            add_id = self._array_add_id
            if add_id is None and widget_id:
                add_id = f"{widget_id}--add"
            row = Horizontal(
                Input(placeholder="Add item and press Enter", id=input_id),
                Button("Add", id=add_id),
                id=self._array_row_id,
                classes=self._array_row_class,
            )
            self._container.mount(self._label_widget(label), lv, row)
            return row.query_one(Input), array_values

        inp = Input(placeholder=label, id=widget_id)
        if value is not None:
            inp.value = str(value)
        if self._include_input_label:
            self._container.mount(self._label_widget(label), inp)
        else:
            self._container.mount(inp)
        return inp, None

    def _label_widget(self, text: str) -> Static:
        if self._label_class:
            return Static(text, classes=self._label_class)
        return Static(text)

    @staticmethod
    def _build_label(name: str, spec: Dict[str, Any], required: bool) -> str:
        label = name
        if spec.get("description"):
            label += f" — {spec['description']}"
        default = spec.get("default")
        if default is not None:
            label += f" [default: {default}]"
        if required:
            label += " *"
        return label

    @staticmethod
    def is_free_text_array(spec: Dict[str, Any]) -> bool:
        if spec.get("type") != "array":
            return False
        items_spec = spec.get("items", {})
        return "oneOf" not in items_spec and "enum" not in items_spec

    @staticmethod
    def handle_array_key(event, lv: ListView, inp: Input, values: List[Any]) -> bool:
        if event.key == "up" and values:
            if lv.index is None:
                lv.index = len(values) - 1
            elif lv.index > 0:
                lv.index -= 1
            event.prevent_default()
            event.stop()
            return True
        if event.key == "down" and lv.index is not None:
            if lv.index < len(values) - 1:
                lv.index += 1
            else:
                lv.index = None
            event.prevent_default()
            event.stop()
            return True
        if event.key in ("backspace", "delete") and not inp.value and lv.index is not None:
            FieldRender._remove_array_item(lv, lv.index, values)
            event.prevent_default()
            event.stop()
            return True
        return False

    @staticmethod
    def _remove_array_item(lv: ListView, idx: int, values: List[Any]) -> None:
        if idx < 0 or idx >= len(values):
            return
        values.pop(idx)
        lv.children[idx].remove()
        if not values:
            lv.index = None
        elif idx >= len(values):
            lv.index = len(values) - 1


class SchemaForm(Vertical):
    """Reusable JSON-Schema form renderer for multiple fields at once."""

    DEFAULT_CSS = """
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

    def __init__(
        self,
        schema: Dict[str, Any],
        initial_values: Optional[Dict[str, Any]] = None,
        id_prefix: str = "cfg",
        required: Optional[List[str]] = None,
    ) -> None:
        super().__init__()
        self._schema = schema
        self._properties = schema.get("properties", {})
        self._required = set(required or schema.get("required", []))
        self._initial_values: Dict[str, Any] = dict(initial_values or {})
        self._id_prefix = id_prefix
        self._array_values: Dict[str, List[Any]] = {}

    def on_mount(self) -> None:
        self.render_form()

    def on_key(self, event) -> None:
        focused = self.app.focused
        base_id: Optional[str] = None
        inp: Optional[Input] = None
        lv: Optional[ListView] = None

        if isinstance(focused, Input) and focused.id and focused.id.endswith("--input"):
            inp = focused
            base_id = focused.id.removesuffix("--input")
        elif isinstance(focused, ListView) and focused.id:
            lv = focused
            base_id = focused.id
        elif isinstance(focused, Button) and focused.id and focused.id.endswith("--add"):
            base_id = focused.id.removesuffix("--add")

        if base_id is None:
            return

        prefix = f"{self._id_prefix}-"
        if not base_id.startswith(prefix):
            return

        field_name = base_id[len(prefix):]
        spec = self._properties.get(field_name, {})
        if not FieldRender.is_free_text_array(spec):
            return

        try:
            if lv is None:
                lv = self.query_one(f"#{base_id}", ListView)
            if inp is None:
                inp = self.query_one(f"#{base_id}--input", Input)
        except Exception:
            return

        values = self._array_values.get(field_name, [])
        if FieldRender.handle_array_key(event, lv, inp, values):
            self._array_values[field_name] = values
            return

    def render_form(self) -> None:
        self.remove_children()
        renderer = FieldRender(
            self,
            id_prefix=self._id_prefix,
            label_class="config-field-label",
            include_input_label=True,
            array_items_class="config-array-items",
            array_row_class="config-array-row",
        )
        for name, spec in self._properties.items():
            value = self._initial_values.get(name, spec.get("default"))
            _, array_values = renderer.render(
                name, spec, name in self._required, value
            )
            if array_values is not None:
                self._array_values[name] = array_values

    def get_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for name, spec in self._properties.items():
            val = self._read_field_value(name, spec)
            if val is not None:
                values[name] = val
        return values

    def handle_array_add(self, button_id: str) -> Optional[str]:
        base_id = button_id.removesuffix("--add")
        input_id = f"{base_id}--input"
        try:
            inp = self.query_one(f"#{input_id}", Input)
            lv = self.query_one(f"#{base_id}", ListView)
        except Exception:
            return None

        raw = inp.value.strip()
        if not raw:
            return None

        prefix = f"{self._id_prefix}-"
        if not base_id.startswith(prefix):
            return None
        field_name = base_id[len(prefix):]

        spec = self._properties.get(field_name, {})
        items_spec = spec.get("items", {})
        item_type = items_spec.get("type", "string")

        try:
            value = self._cast_value(raw, item_type)
        except ValueError as e:
            return str(e)

        v = Draft202012Validator(items_spec)
        item_errors = [e.message for e in v.iter_errors(value)]
        if item_errors:
            return "\n".join(f"* {e}" for e in item_errors)

        arr = self._array_values.setdefault(field_name, [])
        if spec.get("uniqueItems", False) and value in arr:
            return "Duplicate value not allowed"

        arr.append(value)
        inp.value = ""
        lv.append(ListItem(Label(str(value))))
        inp.focus()
        return None

    def _read_field_value(self, name: str, spec: Dict[str, Any]) -> Any:
        widget_id = f"{self._id_prefix}-{name}"
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
            return list(self._array_values.get(name, []))

        return None

    @staticmethod
    def _cast_value(raw: str, field_type: str) -> Any:
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

# FIXME: add hasChanges to know if the user make changes
class FormDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """Modal Textual dialog that renders a JSON-Schema-driven form
    with incremental validation.

    The dialog walks the user through one field at a time, validating
    each answer before advancing to the next.  Navigation is performed
    with *Next* / *Back* buttons or keyboard shortcuts (Enter / Escape).

    Parameters
    ----------
    schema:
        A JSON Schema (Draft 2020-12) ``object`` definition.  The
        ``properties`` key determines the fields shown and their order.
    initial_values:
        Optional mapping of ``{field_name: value}`` used to pre-populate
        widgets.  Values survive back-navigation because an immutable copy
        is stored separately.

    Returns
    -------
    Optional[Dict[str, Any]]
        The collected form data on success, or ``None`` if the user
        cancels.
    """

    BINDINGS = [
        Binding("escape", "back_or_cancel", "Back / Cancel", show=True),
    ]

    CSS = """
    FormDialog {
        align: center middle;
    }

    #dialog {
        width: 80%;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $panel;
    }

    #errors {
        color: red;
        height: auto;
        margin-top: 1;
    }

    #field {
        margin-top: 1;
    }

    #array-items {
        height: auto;
        max-height: 10;
        margin-top: 1;
    }

    #array-input-row {
        height: auto;
        margin-top: 1;
    }

    #array-input-row Input {
        width: 1fr;
    }

    #array-input-row Button {
        width: auto;
    }

    #array-items > ListItem.--highlight {
        background: $accent 50%;
    }
    """

    def __init__(self, schema: Dict[str, Any], initial_values: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.schema = schema
        self.properties = schema.get("properties", {})
        self.required = set(schema.get("required", []))
        self.field_order = list(self.properties.keys())

        self.index = 0
        self._initial_values: Dict[str, Any] = dict(initial_values or {})
        self.data: Dict[str, Any] = dict(self._initial_values)
        self.current_widget: Optional[Widget] = None
        self._array_values: List[Any] = []

    # ============================================================
    # UI
    # ============================================================

    def compose(self) -> ComposeResult:
        """Build the static widget tree.

        The actual per-field widgets are mounted dynamically by
        :meth:`_render_field` inside the ``#field`` placeholder.
        """
        with Vertical(id="dialog"):
            yield Static("Formulario", id="title")
            yield Static("", id="field")
            yield Static("", id="errors")
            with Horizontal():
                yield Button("Cancel", id="back", variant="error")
                yield Button("Next →", id="next", variant="primary")

    def on_mount(self) -> None:
        """Render the first field once the dialog is mounted."""
        self._render_field()

    # ============================================================
    # Navigation
    # ============================================================

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch button clicks to the appropriate action."""
        match event.button.id:
            case "back":
                self.action_back_or_cancel()
            case "next":
                self._submit_current()
            case "array-add":
                self._add_array_item()

    def _is_free_text_array(self) -> bool:
        """Return ``True`` if the current field is an array without
        predefined options (i.e. not a multi-select).
        """
        field = self.field_order[self.index]
        spec = self.properties[field]
        return FieldRender.is_free_text_array(spec)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts.

        For free-text array fields the arrow keys navigate the item
        list and backspace (when the input is empty) removes the
        currently highlighted item.

        For all other widget types, pressing Enter on a non-input
        widget submits the current field.
        """
        if self._is_free_text_array():
            try:
                lv = self.query_one("#array-items", ListView)
                inp = self.query_one("#array-input", Input)
            except Exception:
                pass
            else:
                if FieldRender.handle_array_key(event, lv, inp, self._array_values):
                    return

        if event.key == "enter":
            focused = self.focused
            if not isinstance(focused, (Button, Input)):
                self._submit_current()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the Enter key inside an :class:`Input` widget.

        For the array input, Enter adds the current text as a new item
        if it is non-empty; otherwise it submits the whole field.
        """
        if event.input.id == "array-input":
            if event.input.value.strip():
                self._add_array_item()
            else:
                self._submit_current()
        else:
            self._submit_current()

    def _get_initial_value(self, field: str):
        """Return the initial value for *field*.

        Resolution order:
        1. ``self.data`` — values already submitted in this session.
        2. ``self._initial_values`` — values passed via the constructor.
        3. The ``default`` keyword from the schema property.
        """
        if field in self.data:
            return self.data[field]
        if field in self._initial_values:
            return self._initial_values[field]
        return self.properties[field].get("default")

    def _add_array_item(self):
        """Read the array input, validate and append to the current list.

        The new value is cast to the type declared in ``items.type``,
        validated against the ``items`` sub-schema and checked for
        uniqueness when ``uniqueItems`` is ``true``.
        """
        try:
            inp = self.query_one("#array-input", Input)
        except Exception:
            return
        raw = inp.value.strip()
        if not raw:
            return

        field = self.field_order[self.index]
        spec = self.properties[field]
        items_spec = spec.get("items", {})
        item_type = items_spec.get("type", "string")

        try:
            value = self._cast_value(raw, item_type)
        except ValueError as e:
            self.query_one("#errors", Static).update(str(e))
            return

        # Validate item against items schema
        v = Draft202012Validator(items_spec)
        item_errors = [e.message for e in v.iter_errors(value)]
        if item_errors:
            self.query_one("#errors", Static).update("\n".join(f"❌ {e}" for e in item_errors))
            return

        unique = spec.get("uniqueItems", False)
        if unique and value in self._array_values:
            self.query_one("#errors", Static).update("❌ Duplicate value not allowed")
            return

        self._array_values.append(value)
        self.query_one("#errors", Static).update("")
        inp.value = ""

        lv = self.query_one("#array-items", ListView)
        lv.append(ListItem(Label(str(value))))

        inp.focus()

    def _go_back(self):
        """Navigate to the previous field.

        The submitted value for the previous field is removed from
        ``self.data`` so that the user can re-enter it.  Original
        initial values are preserved in ``self._initial_values``.
        """
        if self.index == 0:
            return
        field = self.field_order[self.index - 1]
        self.data.pop(field, None)
        self.index -= 1
        self._render_field()

    def action_back_or_cancel(self) -> None:
        """Bound to *Escape*.  Goes back one field or cancels the
        dialog if already on the first field.
        """
        if self.index == 0:
            self.dismiss(None)
        else:
            self._go_back()

    # ============================================================
    # Rendering
    # ============================================================

    def _render_field(self):
        """Replace the contents of the ``#field`` container with the
        widget(s) appropriate for the current schema property.

        The method inspects the property spec to decide which widget to
        use:

        * ``oneOf`` / ``enum`` → :class:`RadioSet`
        * ``type: boolean`` → :class:`Checkbox`
        * ``type: array`` with ``oneOf``/``enum`` items →
          :class:`SelectionList`
        * ``type: array`` (free text) → :class:`ListView` +
          :class:`Input`
        * everything else → :class:`Input`

        After mounting, the *Back* / *Next* button labels are updated
        and focus is moved to the new widget.
        """
        container = self.query_one("#field", Static)
        container.remove_children()
        self.query_one("#errors", Static).update("")

        field = self.field_order[self.index]
        spec = self.properties[field]

        renderer = FieldRender(
            container,
            include_input_label=False,
            selection_list_id="array-selection",
            array_list_id="array-items",
            array_input_id="array-input",
            array_add_id="array-add",
            array_row_id="array-input-row",
        )
        value = self._get_initial_value(field)
        widget, array_values = renderer.render(
            field, spec, field in self.required, value
        )
        if array_values is not None:
            self._array_values = array_values
        self.current_widget = widget

        back_btn = self.query_one("#back", Button)
        if self.index == 0:
            back_btn.label = "Cancel"
            back_btn.variant = "error"
        else:
            back_btn.label = "← Back"
            back_btn.variant = "error"

        next_btn = self.query_one("#next", Button)
        if self.index >= len(self.field_order) - 1:
            next_btn.label = "Ok"
        else:
            next_btn.label = "Next →"

        if isinstance(self.current_widget, Widget):
            self.call_after_refresh(self.current_widget.focus)

    # ============================================================
    # Validation
    # ============================================================

    def _submit_current(self):
        """Validate and store the current field, then advance.

        If the field value is ``None`` and there is a schema default it
        is used.  Optional fields that are left blank are skipped.
        When all fields have been collected, a final full-schema
        validation is performed before dismissing the dialog.
        """
        field = self.field_order[self.index]
        spec = self.properties[field]

        value = self._read_widget_value()

        if value is None and "default" in spec:
            value = spec["default"]

        if value is None and field not in self.required:
            self.index += 1
            if self.index >= len(self.field_order):
                try:
                    validate(self.data, self.schema)
                except ValidationError as e:
                    self.query_one("#errors", Static).update(str(e.message))
                    self.index -= 1
                    return
                self.dismiss(self.data)
                return
            self._render_field()
            return

        errors = self._validate_field_incremental(field, value)

        if errors:
            self.query_one("#errors", Static).update("\n".join(f"❌ {e}" for e in errors))
            return

        self.data[field] = value
        self.index += 1

        if self.index >= len(self.field_order):
            try:
                validate(self.data, self.schema)
            except ValidationError as e:
                self.query_one("#errors", Static).update(str(e.message))
                self.index -= 1
                return
            self.dismiss(self.data)
            return

        self._render_field()

    def _read_widget_value(self):
        """Extract the current value from the active widget.

        Returns
        -------
        Any
            The typed value, or ``None`` when the widget is empty /
            has no selection.
        """
        field = self.field_order[self.index]
        spec = self.properties[field]
        w = self.current_widget

        if isinstance(w, SelectionList):
            return list(w.selected)

        if isinstance(w, Input):
            # Free-text array: the Input is just for adding items
            if spec.get("type") == "array":
                return list(self._array_values)
            raw = w.value.strip()
            if not raw:
                return None
            return self._cast_value(raw, spec.get("type", "string"))

        if isinstance(w, Checkbox):
            return w.value

        if isinstance(w, RadioSet):
            for btn in w.query(RadioButton):
                if btn.value:
                    return btn.id
            return None

        return None

    def _validate_field_incremental(self, field_name: str, candidate_value: Any) -> List[str]:
        """Validate *candidate_value* for *field_name* against a sub-schema
        that only includes fields seen so far.

        This enables cross-field constraints (``allOf``, ``if``/``then``,
        etc.) to fire as soon as the relevant fields have been filled in,
        without requiring all fields to be present.

        Parameters
        ----------
        field_name:
            Name of the property being validated.
        candidate_value:
            The value the user entered for this field.

        Returns
        -------
        List[str]
            A list of human-readable error messages.  Empty when valid.
        """
        idx = self.field_order.index(field_name)
        visible = set(self.field_order[: idx + 1])

        props = {k: v for k, v in self.properties.items() if k in visible}
        req = [k for k in self.required if k in visible]

        subschema = {
            "type": "object",
            "properties": props,
            "required": req,
        }

        for kw in ("allOf", "anyOf", "oneOf", "if", "then", "else"):
            if kw in self.schema:
                subschema[kw] = self.schema[kw]

        instance = dict(self.data)
        instance[field_name] = candidate_value

        v = Draft202012Validator(subschema)
        return [e.message for e in v.iter_errors(instance)]

    # ============================================================

    def _cast_value(self, raw: str, field_type: str):
        """Convert the raw string *raw* to the Python type implied by
        *field_type*.

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
            The converted value.

        Raises
        ------
        ValueError
            If the conversion fails or the type is unsupported.
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
