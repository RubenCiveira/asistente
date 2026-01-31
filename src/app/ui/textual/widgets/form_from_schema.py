"""JSON-Schema-driven form that renders all fields at once."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual.containers import Vertical

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

    .config-array-header {
        text-style: bold;
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
        self._fields: Dict[str, FieldFromSchema] = {}

    def on_mount(self) -> None:
        self.render_form()

    def render_form(self) -> None:
        self.remove_children()
        for name, spec in self._properties.items():
            value = self._initial_values.get(name, spec.get("default"))
            spec_copy = dict(spec)
            if name in self._required:
                spec_copy["x-required"] = True
            field = FieldFromSchema(
                name,
                spec_copy,
                initial_value=value,
                mode="form",
                object_array_mode="modal",
            )
            self._fields[name] = field
            self.mount(field)

    def get_values(self) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for name, field in self._fields.items():
            val = field.get_value()
            if val is not None:
                values[name] = val
        return values

    def is_valid(self) -> bool:
        valid = True
        for field in self._fields.values():
            if not field.is_valid():
                valid = False
        return valid
