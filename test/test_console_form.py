"""Tests for app.ui.console.form.ConsoleFormRenderer."""

from __future__ import annotations

from unittest.mock import patch
import pytest

from app.ui.console.form import ConsoleFormRenderer, _EscapePressed


class TestCastValue:
    def setup_method(self):
        self.renderer = ConsoleFormRenderer()

    def test_string(self):
        assert self.renderer._cast_value("hello", "string") == "hello"

    def test_integer(self):
        assert self.renderer._cast_value("42", "integer") == 42

    def test_integer_bad(self):
        with pytest.raises(ValueError):
            self.renderer._cast_value("abc", "integer")

    def test_number(self):
        assert self.renderer._cast_value("3.14", "number") == pytest.approx(3.14)

    def test_boolean_true(self):
        for v in ("true", "True", "yes", "Y", "1"):
            assert self.renderer._cast_value(v, "boolean") is True

    def test_boolean_false(self):
        for v in ("false", "False", "no", "N", "0"):
            assert self.renderer._cast_value(v, "boolean") is False

    def test_boolean_bad(self):
        with pytest.raises(ValueError, match="boolean"):
            self.renderer._cast_value("maybe", "boolean")

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            self.renderer._cast_value("x", "object")


class TestValidateFieldIncremental:
    def test_valid_string(self):
        r = ConsoleFormRenderer()
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        r.schema = schema
        r.field_order = ["name"]
        errors = r._validate_field_incremental(
            field_name="name", candidate_value="Alice", partial_data={}
        )
        assert errors == []

    def test_minimum_constraint(self):
        r = ConsoleFormRenderer()
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer", "minimum": 1}},
            "required": ["count"],
        }
        r.schema = schema
        r.field_order = ["count"]
        errors = r._validate_field_incremental(
            field_name="count", candidate_value=0, partial_data={}
        )
        assert len(errors) > 0


class TestAskForm:
    def test_rejects_non_object_schema(self):
        r = ConsoleFormRenderer()
        with pytest.raises(ValueError, match="object"):
            r.ask_form({"type": "array"})

    def test_single_field_form(self):
        r = ConsoleFormRenderer()
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        with patch.object(r, "_prompt", return_value="Alice"):
            result = r.ask_form(schema)
        assert result == {"name": "Alice"}

    def test_cancel_on_first_field(self):
        r = ConsoleFormRenderer()
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        with patch.object(r, "_prompt", side_effect=_EscapePressed):
            result = r.ask_form(schema)
        assert result is None

    def test_keyboard_interrupt_cancels(self):
        r = ConsoleFormRenderer()
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        with patch.object(r, "_prompt", side_effect=KeyboardInterrupt):
            result = r.ask_form(schema)
        assert result is None


class TestValidateArrayItem:
    def test_valid_item(self):
        r = ConsoleFormRenderer()
        errors = r._validate_array_item("hello", {"type": "string"})
        assert errors == []

    def test_invalid_item(self):
        r = ConsoleFormRenderer()
        errors = r._validate_array_item("hello", {"type": "integer"})
        assert len(errors) > 0
