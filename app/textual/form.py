from typing import Any, Dict, List, Optional
from textual.app import ComposeResult
from textual.screen import ModalScreen
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


class FormDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """
    Modal Textual dialog that renders a JSON-Schema-driven form
    with incremental validation.
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
    """

    def __init__(self, schema: Dict[str, Any]):
        super().__init__()
        self.schema = schema
        self.properties = schema.get("properties", {})
        self.required = set(schema.get("required", []))
        self.field_order = list(self.properties.keys())

        self.index = 0
        self.data: Dict[str, Any] = {}
        self.current_widget = None
        self._array_values: List[Any] = []

    # ============================================================
    # UI
    # ============================================================

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Formulario", id="title")
            yield Static("", id="field")
            yield Static("", id="errors")
            with Horizontal():
                yield Button("← Back", id="back")
                yield Button("Cancel", id="cancel", variant="error")
                yield Button("Next →", id="next", variant="primary")

    def on_mount(self) -> None:
        self._render_field()

    # ============================================================
    # Navigation
    # ============================================================

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "cancel":
                self.dismiss(None)
            case "back":
                self._go_back()
            case "next":
                self._submit_current()
            case "array-add":
                self._add_array_item()

    def on_key(self, event) -> None:
        if event.key == "enter":
            focused = self.focused
            if not isinstance(focused, (Button, Input)):
                self._submit_current()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "array-input":
            self._add_array_item()
        else:
            self._submit_current()

    def _add_array_item(self):
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
        if self.index == 0:
            return
        field = self.field_order[self.index - 1]
        self.data.pop(field, None)
        self.index -= 1
        self._render_field()

    def action_back_or_cancel(self) -> None:
        if self.index == 0:
            self.dismiss(None)
        else:
            self._go_back()

    # ============================================================
    # Rendering
    # ============================================================

    def _render_field(self):
        container = self.query_one("#field", Static)
        container.remove_children()
        self.query_one("#errors", Static).update("")

        field = self.field_order[self.index]
        spec = self.properties[field]

        label = field
        if spec.get("description"):
            label += f" — {spec['description']}"
        default = spec.get("default")
        if default is not None:
            label += f" [default: {default}]"
        if field in self.required:
            label += " *"

        if "oneOf" in spec:
            buttons = [RadioButton(opt.get("title", opt["const"]), id=str(opt["const"])) for opt in spec["oneOf"]]
            rs = RadioSet(*buttons)
            self.current_widget = rs
            container.mount(Static(label), rs)

        elif "enum" in spec:
            buttons = [RadioButton(str(opt), id=str(opt)) for opt in spec["enum"]]
            rs = RadioSet(*buttons)
            self.current_widget = rs
            container.mount(Static(label), rs)

        elif spec.get("type") == "boolean":
            cb = Checkbox(label)
            self.current_widget = cb
            container.mount(cb)

        elif spec.get("type") == "array":
            items_spec = spec.get("items", {})
            # Multi-select: items have oneOf or enum
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

                sl = SelectionList[str](*options, id="array-selection")
                self.current_widget = sl
                container.mount(Static(label), sl)
            else:
                # Free-text array
                self._array_values = []
                lv = ListView(id="array-items")
                inp = Input(placeholder="Add item and press Enter", id="array-input")
                self.current_widget = inp
                container.mount(Static(label), lv, Horizontal(inp, Button("Add", id="array-add"), id="array-input-row"))

        else:
            inp = Input(placeholder=label)
            self.current_widget = inp
            container.mount(inp)

        next_btn = self.query_one("#next", Button)
        if self.index >= len(self.field_order) - 1:
            next_btn.label = "Ok"
        else:
            next_btn.label = "Next →"

        self.call_after_refresh(self.current_widget.focus)

    # ============================================================
    # Validation
    # ============================================================

    def _submit_current(self):
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
            btn = w.pressed_button
            if btn:
                return btn.id
            return None

        return None

    def _validate_field_incremental(self, field_name: str, candidate_value: Any) -> List[str]:
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
