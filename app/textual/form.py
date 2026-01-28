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
)
from textual.containers import Vertical, Horizontal
from jsonschema import Draft202012Validator, validate, ValidationError


class FormDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """
    Modal Textual dialog that renders a JSON-Schema-driven form
    with incremental validation.
    """

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

    def _go_back(self):
        if self.index == 0:
            return
        field = self.field_order[self.index - 1]
        self.data.pop(field, None)
        self.index -= 1
        self._render_field()

    # ============================================================
    # Rendering
    # ============================================================

    def _render_field(self):
        container = self.query_one("#field", Static)
        container.update("")
        self.query_one("#errors", Static).update("")

        field = self.field_order[self.index]
        spec = self.properties[field]

        label = field
        if spec.get("description"):
            label += f" — {spec['description']}"
        if field in self.required:
            label += " *"

        if "oneOf" in spec:
            rs = RadioSet()
            for opt in spec["oneOf"]:
                rs.add(RadioButton(opt.get("title", opt["const"]), id=str(opt["const"])))
            self.current_widget = rs
            container.mount(Static(label), rs)

        elif "enum" in spec:
            rs = RadioSet()
            for opt in spec["enum"]:
                rs.add(RadioButton(str(opt), id=str(opt)))
            self.current_widget = rs
            container.mount(Static(label), rs)

        elif spec.get("type") == "boolean":
            cb = Checkbox(label)
            self.current_widget = cb
            container.mount(cb)

        else:
            inp = Input(placeholder=label)
            self.current_widget = inp
            container.mount(inp)

    # ============================================================
    # Validation
    # ============================================================

    def _submit_current(self):
        field = self.field_order[self.index]
        spec = self.properties[field]

        value = self._read_widget_value()
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

        self._render_field()

    def _read_widget_value(self):
        w = self.current_widget
        if isinstance(w, Input):
            raw = w.value.strip()
            if not raw:
                return None
            return self._cast_value(raw, self.properties[self.field_order[self.index]].get("type", "string"))

        if isinstance(w, Checkbox):
            return w.value

        if isinstance(w, RadioSet):
            pressed = w.pressed
            if pressed:
                return pressed.id
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
        raise ValueError(f"Unsupported type {field_type}")
