"""Wizard dialog that renders a JSON-Schema-driven form step by step."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator, validate, ValidationError
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from .field_from_schema import FieldFromSchema


# FIXME: add hasChanges to know if the user make changes
class WizardFromSchema(ModalScreen[Optional[Dict[str, Any]]]):
    """Modal Textual dialog that renders a JSON-Schema-driven form
    with incremental validation.
    """

    BINDINGS = [
        Binding("escape", "back_or_cancel", "Back / Cancel", show=True),
    ]

    CSS = """
    WizardFromSchema {
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
        self.current_field: Optional[FieldFromSchema] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Formulario", id="title")
            yield Static("", id="field")
            yield Static("", id="errors")
            with Horizontal():
                yield Button("Cancel", id="back", variant="error")
                yield Button("Next →", id="next", variant="primary")

    def on_mount(self) -> None:
        self._render_field()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "back":
                self.action_back_or_cancel()
            case "next":
                self._submit_current()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "array-input":
            if event.input.value.strip():
                return
            self._submit_current()
        else:
            self._submit_current()

    def on_key(self, event) -> None:
        if event.key == "enter":
            focused = self.focused
            if not isinstance(focused, (Button, Input)):
                self._submit_current()

    def _get_initial_value(self, field: str):
        if field in self.data:
            return self.data[field]
        if field in self._initial_values:
            return self._initial_values[field]
        return self.properties[field].get("default")

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

    def _render_field(self):
        container = self.query_one("#field", Static)
        container.remove_children()
        self.query_one("#errors", Static).update("")

        field = self.field_order[self.index]
        spec = dict(self.properties[field])
        if field in self.required:
            spec["x-required"] = True
        value = self._get_initial_value(field)

        self.current_field = FieldFromSchema(
            field,
            spec,
            initial_value=value,
            mode="wizard",
            object_array_mode="modal",
        )
        container.mount(self.current_field)

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

    def _submit_current(self):
        field = self.field_order[self.index]
        spec = self.properties[field]
        value = self.current_field.get_value() if self.current_field else None

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
