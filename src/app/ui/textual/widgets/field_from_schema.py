"""Field renderer for JSON-Schema-driven forms."""

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


class FieldFromSchema:
    def __init__(
        self,
        container,
        *,
        id_prefix: Optional[str] = None,
        label_class: Optional[str] = None,
        include_input_label: bool = True,
        object_array_mode: str = "input",
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
        self._object_array_mode = object_array_mode
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
                *[
                    ListItem(Label(self.format_array_item(items_spec, v)))
                    for v in array_values
                ],
                id=lv_id,
                classes=self._array_items_class,
            )
            add_id = self._array_add_id
            if add_id is None and widget_id:
                add_id = f"{widget_id}--add"
            if self._is_object_array(items_spec) and self._object_array_mode == "button_only":
                add_button = Button("Add", id=add_id)
                row = Horizontal(
                    add_button,
                    id=self._array_row_id,
                    classes=self._array_row_class,
                )
                self._container.mount(self._label_widget(label), lv, row)
                return add_button, array_values

            input_id = self._array_input_id
            if input_id is None and widget_id:
                input_id = f"{widget_id}--input"
            input_widget = Input(
                placeholder="Add item and press Enter",
                id=input_id,
            )
            row = Horizontal(
                input_widget,
                Button("Add", id=add_id),
                id=self._array_row_id,
                classes=self._array_row_class,
            )
            self._container.mount(self._label_widget(label), lv, row)
            return input_widget, array_values

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
    def _is_object_array(items_spec: Dict[str, Any]) -> bool:
        return items_spec.get("type") == "object" or "properties" in items_spec

    @staticmethod
    def format_array_item(items_spec: Dict[str, Any], value: Any) -> str:
        if FieldFromSchema._is_object_array(items_spec) and isinstance(value, dict):
            props = items_spec.get("properties", {})
            parts = []
            for key in props.keys():
                val = value.get(key, "")
                parts.append(f"{key}: {val}")
            if parts:
                return " | ".join(parts)
        return str(value)

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
            FieldFromSchema._remove_array_item(lv, lv.index, values)
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