"""Field widget for JSON-Schema-driven forms."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator
from textual.containers import Horizontal, Vertical
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
)

from .path_field import PathField


class FieldFromSchema(Vertical):
    """Render a single JSON-Schema field and manage its interactions."""

    OBJECT_ARRAY_MAX_WIDTH = 24

    def __init__(
        self,
        name: str,
        spec: Dict[str, Any],
        initial_value: Any | None = None,
        *,
        mode: str = "form",
        object_array_mode: str = "modal",
    ) -> None:
        super().__init__()
        self._name = name
        self._spec = dict(spec)
        self._initial_value = initial_value
        self._mode = mode
        self._object_array_mode = object_array_mode
        self._array_values: List[Any] = []
        self._array_widths: Dict[str, int] = {}
        self._errors: List[str] = []
        self._label: Optional[Static] = None
        self._widget: Optional[object] = None
        self._list_view: Optional[ListView] = None
        self._array_input: Optional[Input] = None
        self._header: Optional[Static] = None

    def on_mount(self) -> None:
        self._build()

    def _build(self) -> None:
        self.remove_children()
        label_text = self._build_label(self._name, self._spec, self._is_required())
        self._label = Static(label_text, classes=self._label_class())

        spec = self._spec
        if spec.get("type") == "string" and spec.get("format") == "directory":
            root_dir = None
            if isinstance(spec.get("x-root-dir"), str) and spec.get("x-root-dir"):
                root_dir = self._path_root(spec)
            self._widget = PathField(
                root_dir=root_dir,
                must_exist=spec.get("x-must-exist", True),
                warn_if_exists=spec.get("x-warn-if-exists", False),
                select="dir",
                initial_path=self._path_initial(),
                name_filter=spec.get("x-name-filter"),
                relative_check_path=self._path_relative_check(spec),
                max_suggestions=spec.get("x-max-suggestions", 30),
                placeholder=str(root_dir),
                input_id=self._input_id(),
                autocomplete_id=f"{self._base_id()}--ac",
            )
            if self._include_input_label():
                self.mount(self._label, self._widget)
            else:
                self.mount(self._widget)
            return
        if "oneOf" in spec:
            buttons = []
            for opt in spec["oneOf"]:
                title = opt.get("title", opt.get("const"))
                const = opt.get("const")
                button_id = f"{self._base_id()}--{const}"
                buttons.append(RadioButton(title, id=button_id))
            rs = RadioSet(*buttons, id=self._base_id())
            if self._initial_value is not None:
                selected_id = f"{self._base_id()}--{self._initial_value}"
                for rb in rs.query(RadioButton):
                    if rb.id == selected_id:
                        rb.value = True
                        break
            self._widget = rs
            self.mount(self._label, rs)
            return

        if "enum" in spec:
            buttons = []
            for opt in spec["enum"]:
                button_id = f"{self._base_id()}--{opt}"
                buttons.append(RadioButton(str(opt), id=button_id))
            rs = RadioSet(*buttons, id=self._base_id())
            if self._initial_value is not None:
                selected_id = f"{self._base_id()}--{self._initial_value}"
                for rb in rs.query(RadioButton):
                    if rb.id == selected_id:
                        rb.value = True
                        break
            self._widget = rs
            self.mount(self._label, rs)
            return

        if spec.get("type") == "boolean":
            cb = Checkbox(label_text, id=self._base_id())
            if self._initial_value is not None:
                cb.value = bool(self._initial_value)
            self._widget = cb
            self.mount(cb)
            return

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

                sl = SelectionList[str](*options, id=self._selection_id())
                for v in self._initial_value or []:
                    sl.select(str(v))
                self._widget = sl
                self.mount(self._label, sl)
                return

            self._array_values = list(self._initial_value or [])
            self._array_widths = self._compute_widths(items_spec, self._array_values)
            header_line = self.format_array_header(items_spec, self._array_widths)
            if header_line and self._mode != "wizard":
                self._header = Static(
                    header_line,
                    id=f"{self._list_id()}--header",
                    classes="config-array-header",
                )
                self.mount(self._label, self._header)
            else:
                self.mount(self._label)

            self._list_view = ListView(
                *[
                    ListItem(
                        Label(self.format_array_item(items_spec, v, self._array_widths))
                    )
                    for v in self._array_values
                ],
                id=self._list_id(),
                classes="config-array-items" if self._mode == "form" else None,
            )

            add_id = self._add_id()
            if self._is_object_array(items_spec) and self._object_array_mode == "modal":
                row = Horizontal(
                    Button("Add", id=add_id),
                    id=self._row_id(),
                    classes="config-array-row" if self._mode == "form" else None,
                )
                self.mount(self._list_view, row)
                return

            self._array_input = Input(
                placeholder="Add item and press Enter",
                id=self._input_id(),
            )
            row = Horizontal(
                self._array_input,
                Button("Add", id=add_id),
                id=self._row_id(),
                classes="config-array-row" if self._mode == "form" else None,
            )
            self.mount(self._list_view, row)
            return

        inp = Input(placeholder=label_text, id=self._base_id())
        if self._initial_value is not None:
            inp.value = str(self._initial_value)
        self._widget = inp
        if self._include_input_label():
            self.mount(self._label, inp)
        else:
            self.mount(inp)

    def get_value(self) -> Any:
        if self._spec.get("type") == "array":
            return list(self._array_values)

        if isinstance(self._widget, PathField):
            return self._widget.get_value()

        if isinstance(self._widget, SelectionList):
            return list(self._widget.selected)

        if isinstance(self._widget, RadioSet):
            prefix = f"{self._base_id()}--"
            for btn in self._widget.query(RadioButton):
                if btn.value and btn.id and btn.id.startswith(prefix):
                    raw = btn.id[len(prefix):]
                    return self._cast_value(raw, self._spec.get("type", "string"))
            return None

        if isinstance(self._widget, Checkbox):
            return self._widget.value

        if isinstance(self._widget, Input):
            raw = self._widget.value.strip()
            if not raw:
                return None
            return self._cast_value(raw, self._spec.get("type", "string"))

        return None

    def is_valid(self) -> bool:
        self._errors = []
        value = self.get_value()
        if value is None and not self._is_required():
            return True
        schema = {
            "type": "object",
            "properties": {self._name: self._spec},
            "required": [self._name] if self._is_required() else [],
        }
        instance = {self._name: value}
        v = Draft202012Validator(schema)
        self._errors = [e.message for e in v.iter_errors(instance)]
        return not self._errors

    def get_errors(self) -> List[str]:
        return list(self._errors)

    def has_changed(self) -> bool:
        return self.get_value() != self._initial_value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != self._add_id():
            return
        event.stop()
        self.run_worker(self.add_to_array)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != self._input_id():
            return
        self.run_worker(self.add_to_array)

    def focus_first(self) -> None:
        if isinstance(self._widget, PathField):
            self._widget.focus_input()
            return
        for widget_type in (Input, SelectionList, RadioSet, Checkbox, Button):
            try:
                widget = self.query_one(widget_type)
            except Exception:
                continue
            widget.focus()
            return

    def on_key(self, event) -> None:
        if self._list_view is None:
            return
        if event.key == "up" and self._array_values:
            if self._list_view.index is None:
                self._list_view.index = len(self._array_values) - 1
            elif self._list_view.index > 0:
                self._list_view.index -= 1
            event.prevent_default()
            event.stop()
            return
        if event.key == "down" and self._list_view.index is not None:
            if self._list_view.index < len(self._array_values) - 1:
                self._list_view.index += 1
            else:
                self._list_view.index = None
            event.prevent_default()
            event.stop()
            return
        if event.key in ("backspace", "delete") and self._list_view.index is not None:
            if self._array_input is not None and self._array_input.value:
                return
            idx = self._list_view.index
            if idx is None or idx < 0 or idx >= len(self._array_values):
                return
            self._array_values.pop(idx)
            self._list_view.children[idx].remove()
            if not self._array_values:
                self._list_view.index = None
            elif idx >= len(self._array_values):
                self._list_view.index = len(self._array_values) - 1
            event.prevent_default()
            event.stop()

    async def add_to_array(self) -> Optional[str]:
        spec = self._spec
        items_spec = spec.get("items", {})

        if self._is_object_array(items_spec):
            from .wizard_from_schema import WizardFromSchema

            item_schema = dict(items_spec)
            item_schema.setdefault("type", "object")
            result = await self.app.push_screen_wait(WizardFromSchema(item_schema))
            if result is None:
                return None
            value = result
        else:
            if self._array_input is None:
                return None
            raw = self._array_input.value.strip()
            if not raw:
                return None
            item_type = items_spec.get("type", "string")
            try:
                value = self._cast_value(raw, item_type)
            except ValueError as e:
                return str(e)

        v = Draft202012Validator(items_spec)
        item_errors = [e.message for e in v.iter_errors(value)]
        if item_errors:
            return "\n".join(f"* {e}" for e in item_errors)

        if spec.get("uniqueItems", False) and value in self._array_values:
            return "Duplicate value not allowed"

        self._array_values.append(value)
        if self._array_input is not None and not self._is_object_array(items_spec):
            self._array_input.value = ""
            self._array_input.focus()

        if self._list_view is None:
            return None

        self._array_widths = self._compute_widths(items_spec, self._array_values)
        self._list_view.append(
            ListItem(Label(self.format_array_item(items_spec, value, self._array_widths)))
        )

        if self._header is not None:
            self._header.update(self.format_array_header(items_spec, self._array_widths))
        for idx, li in enumerate(self._list_view.children):
            if idx >= len(self._array_values):
                break
            try:
                label = li.query_one(Label)
            except Exception:
                continue
            label.update(
                self.format_array_item(items_spec, self._array_values[idx], self._array_widths)
            )
        return None

    def _label_class(self) -> Optional[str]:
        if self._mode == "form":
            return "config-field-label"
        return None

    def _include_input_label(self) -> bool:
        return self._mode == "form"

    def _is_required(self) -> bool:
        return bool(self._spec.get("x-required", False))

    def _base_id(self) -> str:
        if self._mode == "wizard":
            return self._name
        return f"cfg-{self._name}"

    def _list_id(self) -> str:
        return "array-items" if self._mode == "wizard" else self._base_id()

    def _input_id(self) -> str:
        return "array-input" if self._mode == "wizard" else f"{self._base_id()}--input"

    def _add_id(self) -> str:
        return "array-add" if self._mode == "wizard" else f"{self._base_id()}--add"

    def _row_id(self) -> str | None:
        return "array-input-row" if self._mode == "wizard" else None

    def _selection_id(self) -> str:
        return "array-selection" if self._mode == "wizard" else self._base_id()

    def _path_root(self, spec: Dict[str, Any]) -> Path:
        root = spec.get("x-root-dir")
        if isinstance(root, str) and root:
            return Path(root).expanduser().resolve()
        return Path.home()

    def _path_initial(self) -> Path | None:
        initial = self._spec.get("x-initial-dir")
        if isinstance(initial, str) and initial:
            return Path(initial).expanduser()
        if self._initial_value is not None:
            return Path(str(self._initial_value)).expanduser()
        return Path.home()

    def _path_relative_check(self, spec: Dict[str, Any]) -> Path | None:
        rel = spec.get("x-relative-check-path")
        if isinstance(rel, str) and rel:
            return Path(rel)
        return None

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
    def _is_object_array(items_spec: Dict[str, Any]) -> bool:
        return items_spec.get("type") == "object" or "properties" in items_spec

    def _compute_widths(
        self,
        items_spec: Dict[str, Any],
        values: List[Any],
    ) -> Dict[str, int]:
        max_width = items_spec.get("x-maxWidth")
        if not isinstance(max_width, int):
            max_width = self.OBJECT_ARRAY_MAX_WIDTH
        props = items_spec.get("properties", {})
        overrides = items_spec.get("x-column-widths", {})
        widths: Dict[str, int] = {}
        for key in props.keys():
            prop_spec = props.get(key, {})
            if isinstance(overrides, dict) and key in overrides:
                try:
                    widths[key] = max(1, int(overrides[key]))
                    continue
                except (TypeError, ValueError):
                    pass
            if "x-width" in prop_spec:
                try:
                    widths[key] = max(1, int(prop_spec["x-width"]))
                    continue
                except (TypeError, ValueError):
                    pass

            best = len(str(key))
            for item in values:
                if isinstance(item, dict):
                    raw = str(item.get(key, ""))
                else:
                    raw = ""
                best = max(best, len(raw))
            widths[key] = min(max_width, best)
        return widths

    @staticmethod
    def format_array_header(
        items_spec: Dict[str, Any],
        widths: Optional[Dict[str, int]],
    ) -> str:
        props = items_spec.get("properties", {})
        if not props:
            return ""
        parts = []
        for key in props.keys():
            width = widths.get(key, len(key)) if widths else len(key)
            trim, side = FieldFromSchema._trim_config(props.get(key, {}))
            if width and trim:
                cell = FieldFromSchema._trim_pad(str(key), width, side)
            elif width:
                cell = str(key).ljust(width)
            else:
                cell = str(key)
            parts.append(cell)
        return " | ".join(parts)

    @staticmethod
    def format_array_item(
        items_spec: Dict[str, Any],
        value: Any,
        widths: Optional[Dict[str, int]] = None,
    ) -> str:
        if FieldFromSchema._is_object_array(items_spec) and isinstance(value, dict):
            props = items_spec.get("properties", {})
            parts = []
            for key in props.keys():
                val = value.get(key, "")
                width = widths.get(key, 0) if widths else 0
                trim, side = FieldFromSchema._trim_config(props.get(key, {}))
                if width and trim:
                    cell = FieldFromSchema._trim_pad(str(val), width, side)
                elif width:
                    cell = str(val).ljust(width)
                else:
                    cell = str(val)
                parts.append(cell)
            if parts:
                return " | ".join(parts)
        return str(value)

    @staticmethod
    def _trim_pad(value: str, width: int, side: str = "right") -> str:
        if width <= 0:
            return value
        text = value
        if len(text) > width:
            if width <= 3:
                text = text[:width]
            else:
                if side == "left":
                    text = "..." + text[len(text) - (width - 3):]
                else:
                    text = text[: width - 3] + "..."
        return text.ljust(width)

    @staticmethod
    def _trim_config(prop_spec: Dict[str, Any]) -> tuple[bool, str]:
        trim = prop_spec.get("x-trim", True)
        if not isinstance(trim, bool):
            trim = True
        side = str(prop_spec.get("x-trim-side", "right")).lower()
        if side not in ("left", "right"):
            side = "right"
        return trim, side

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
