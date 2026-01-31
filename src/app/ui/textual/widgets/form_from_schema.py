"""JSON-Schema-driven form that renders all fields at once."""

from __future__ import annotations

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


from .field_from_schema import FieldFromSchema

class FormFromSchema(Vertical):
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
        if not FieldFromSchema.is_free_text_array(spec):
            return

        try:
            if lv is None:
                lv = self.query_one(f"#{base_id}", ListView)
            if inp is None:
                inp = self.query_one(f"#{base_id}--input", Input)
        except Exception:
            return

        values = self._array_values.get(field_name, [])
        if FieldFromSchema.handle_array_key(event, lv, inp, values):
            self._array_values[field_name] = values
            return

    def render_form(self) -> None:
        self.remove_children()
        renderer = FieldFromSchema(
            self,
            id_prefix=self._id_prefix,
            label_class="config-field-label",
            include_input_label=True,
            object_array_mode="button_only",
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

    async def handle_array_add(self, button_id: str) -> Optional[str]:
        inp: Optional[Input] = None
        value: Any
        base_id = button_id.removesuffix("--add")
        input_id = f"{base_id}--input"
        prefix = f"{self._id_prefix}-"
        if not base_id.startswith(prefix):
            return None
        field_name = base_id[len(prefix):]

        spec = self._properties.get(field_name, {})
        items_spec = spec.get("items", {})
        if FieldFromSchema._is_object_array(items_spec):
            item_schema = dict(items_spec)
            item_schema.setdefault("type", "object")
            result = await self.app.push_screen_wait(FormDialog(item_schema))
            if result is None:
                return None
            value = result
        else:
            try:
                inp = self.query_one(f"#{input_id}", Input)
            except Exception:
                return None

            raw = inp.value.strip()
            if not raw:
                return None

            item_type = items_spec.get("type", "string")

            try:
                value = self._cast_value(raw, item_type)
            except ValueError as e:
                return str(e)

        try:
            lv = self.query_one(f"#{base_id}", ListView)
        except Exception:
            return None

        v = Draft202012Validator(items_spec)
        item_errors = [e.message for e in v.iter_errors(value)]
        if item_errors:
            return "\n".join(f"* {e}" for e in item_errors)

        arr = self._array_values.setdefault(field_name, [])
        if spec.get("uniqueItems", False) and value in arr:
            return "Duplicate value not allowed"

        arr.append(value)
        if not FieldFromSchema._is_object_array(items_spec):
            if inp is not None:
                inp.value = ""
                inp.focus()
        lv.append(ListItem(Label(FieldFromSchema.format_array_item(items_spec, value))))
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