"""Console (prompt_toolkit) form renderer driven by JSON Schema.

Provides an interactive, field-by-field form in the terminal.  Each field
is prompted according to its JSON Schema type (scalar, enum, oneOf, array)
with incremental cross-field validation.  The user can navigate backwards
with Escape and cancel the form entirely from the first field.
"""

from typing import Any, Dict, List
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from jsonschema import (
    validate,
    Draft202012Validator,
    ValidationError as JsonSchemaError,
)


class _EscapePressed(Exception):
    """Sentinel exception raised when the user presses Escape during input."""


class ConsoleFormRenderer:
    """Interactive terminal form renderer backed by JSON Schema.

    Walks the user through each property defined in the schema, validates
    input incrementally and returns the collected data as a ``dict``.

    Attributes:
        schema: The full JSON Schema currently being rendered.
        field_order: Ordered list of property names to prompt.
    """

    def __init__(self) -> None:
        self.schema: Dict[str, Any] | None = None
        self.field_order: List[str] = []
        self._kb = KeyBindings()

        @self._kb.add("escape")
        def _(event):
            event.app.exit(exception=_EscapePressed())

    def _prompt(self, message: str) -> str:
        """Display *message* and return the user's input line."""
        return prompt(message, key_bindings=self._kb)

    # ============================================================
    # PUBLIC API
    # ============================================================

    def ask_form(self, json_schema: Dict[str, Any]) -> Dict[str, Any] | None:
        """Prompt the user for every field in *json_schema* and return the result.

        Args:
            json_schema: A JSON Schema with ``type: "object"``.

        Returns:
            A ``dict`` of collected values, or ``None`` if the user cancels.

        Raises:
            ValueError: If the schema type is not ``"object"``.
        """
        if json_schema.get("type") != "object":
            raise ValueError("Only JSON Schema with type=object is supported")

        self.schema = json_schema
        properties = json_schema.get("properties", {})
        required = set(json_schema.get("required", []))
        self.field_order = list(properties.keys())

        data: Dict[str, Any] = {}

        print("\n=== FORM INPUT ===")

        try:
            i = 0
            while i < len(self.field_order):
                field = self.field_order[i]
                spec = properties[field]

                try:
                    while True:
                        value = self._ask_field(
                            name=field,
                            spec=spec,
                            required=field in required,
                            partial_data=data,
                        )

                        # Campo opcional sin valor
                        if value is None and field not in required:
                            break

                        errors = self._validate_field_incremental(
                            field_name=field,
                            candidate_value=value,
                            partial_data=data,
                        )

                        if errors:
                            for e in errors:
                                print(f"❌ {e}")
                            print("Please try again.\n")
                            continue

                        data[field] = value
                        break
                except _EscapePressed:
                    if i == 0:
                        print("\n⚠ Form cancelled.")
                        return None
                    i -= 1
                    data.pop(self.field_order[i], None)
                    continue

                i += 1
        except (KeyboardInterrupt, EOFError):
            print("\n⚠ Form cancelled.")
            return None

        # Validación final completa
        try:
            validate(instance=data, schema=json_schema)
        except JsonSchemaError as e:
            print("\n❌ Final validation error:", e.message)
            raise

        return data

    # ============================================================
    # INCREMENTAL VALIDATION
    # ============================================================

    def _validate_field_incremental(
        self,
        *,
        field_name: str,
        candidate_value: Any,
        partial_data: Dict[str, Any],
    ) -> List[str]:
        """Validate a single field in the context of previously filled fields.

        Builds a sub-schema containing only the fields visible so far and
        runs Draft 2020-12 validation against it.

        Args:
            field_name: Name of the field being validated.
            candidate_value: Value the user entered for the field.
            partial_data: Values already collected for earlier fields.

        Returns:
            A list of human-readable error messages (empty on success).
        """

        assert self.schema is not None

        properties = self.schema.get("properties", {})
        required = set(self.schema.get("required", []))

        idx = self.field_order.index(field_name)
        visible_fields = set(self.field_order[: idx + 1])

        subschema: Dict[str, Any] = {
            "type": "object",
            "properties": {
                k: v for k, v in properties.items() if k in visible_fields
            },
            "required": [k for k in required if k in visible_fields],
        }

        # Copiamos keywords de validación cruzada
        for keyword in ("allOf", "anyOf", "oneOf", "if", "then", "else"):
            if keyword in self.schema:
                subschema[keyword] = self.schema[keyword]

        instance = dict(partial_data)
        instance[field_name] = candidate_value

        validator = Draft202012Validator(subschema)
        errors = list(validator.iter_errors(instance))

        return [e.message for e in errors]

    # ============================================================
    # INPUT HANDLING
    # ============================================================

    def _ask_field(self, name: str, spec: Dict[str, Any], required: bool, partial_data: Dict[str, Any] | None = None):
        """Prompt for a single field, dispatching to the appropriate input handler."""
        description = spec.get("description", "")
        default = spec.get("default")

        label = name
        if description:
            label += f" — {description}"
        if default is not None:
            label += f" [default: {default}]"
        if required:
            label += " *"

        if spec.get("type") == "array":
            return self._ask_array(label, spec, required, field_name=name, partial_data=partial_data or {})

        if "oneOf" in spec:
            return self._ask_one_of(label, spec["oneOf"], default, required)

        if "enum" in spec:
            return self._ask_enum(
                label,
                enum=spec["enum"],
                default=default,
                required=required,
                field_type=spec.get("type", "string"),
            )

        return self._ask_scalar(
            label,
            field_type=spec.get("type", "string"),
            default=default,
            required=required,
        )

    # ============================================================
    # FIELD TYPES
    # ============================================================

    def _ask_scalar(self, label, field_type, default, required):
        """Prompt for a simple scalar value (string, integer, number, boolean)."""
        label += ": "

        while True:
            text = self._prompt(label).strip()

            if not text:
                if default is not None:
                    return default
                if required:
                    print("❌ This field is required")
                    continue
                return None

            try:
                return self._cast_value(text, field_type)
            except ValueError as e:
                print(f"❌ {e}")

    def _ask_enum(self, label, enum, default, required, field_type):
        """Prompt for a value from a fixed set of allowed values."""
        print(f"\n{label}:")
        for i, opt in enumerate(enum, start=1):
            print(f"  {i}) {opt}")

        hint = "Choose an option"
        if default is not None:
            hint += f" (Enter for default={default})"
        hint += ": "

        while True:
            text = self._prompt(hint).strip()

            if not text:
                if default is not None:
                    return default
                if required:
                    print("❌ This field is required")
                    continue
                return None

            if text.isdigit():
                idx = int(text)
                if 1 <= idx <= len(enum):
                    return enum[idx - 1]
                print("❌ Invalid selection")
                continue

            try:
                value = self._cast_value(text, field_type)
            except ValueError as e:
                print(f"❌ {e}")
                continue

            if value in enum:
                return value

            print("❌ Invalid option")

    def _ask_one_of(self, label, options, default, required):
        """Prompt for a selection from a ``oneOf`` list of titled constants."""
        print(f"\n{label}:")
        values = []

        for i, opt in enumerate(options, start=1):
            value = opt.get("const")
            title = opt.get("title", str(value))
            values.append(value)
            print(f"  {i}) {title}")

        hint = "Choose an option"
        if default is not None:
            hint += f" (Enter for default={default})"
        hint += ": "

        while True:
            text = self._prompt(hint).strip()

            if not text:
                if default is not None:
                    return default
                if required:
                    print("❌ This field is required")
                    continue
                return None

            if text.isdigit():
                idx = int(text)
                if 1 <= idx <= len(values):
                    return values[idx - 1]
                print("❌ Invalid selection")
                continue

            if text in values:
                return text

            print("❌ Invalid option")

    def _ask_array(self, label, spec, required, field_name, partial_data):
        """Prompt for an array value (multi-select or free-text items)."""
        items = spec.get("items", {})
        default = spec.get("default", [])
        min_items = spec.get("minItems", 0)
        max_items = spec.get("maxItems")
        unique = spec.get("uniqueItems", False)

        print(f"\n{label}:")

        # Multi-select
        if "oneOf" in items or "enum" in items:
            options = []
            titles = []

            if "oneOf" in items:
                for opt in items["oneOf"]:
                    options.append(opt.get("const"))
                    titles.append(opt.get("title", str(opt.get("const"))))
            else:
                options = items["enum"]
                titles = [str(o) for o in options]

            for i, title in enumerate(titles, start=1):
                print(f"  {i}) {title}")

            hint = "Select options (comma separated"
            if default:
                hint += f", Enter for default={default}"
            hint += "): "

            while True:
                text = self._prompt(hint).strip()

                if not text:
                    if default:
                        return default
                    if required or min_items > 0:
                        print("❌ At least one value is required")
                        continue
                    return []

                try:
                    idxs = [int(x.strip()) for x in text.split(",")]
                    values = [options[i - 1] for i in idxs if 1 <= i <= len(options)]
                except Exception:
                    print("❌ Invalid selection")
                    continue

                if unique:
                    values = list(dict.fromkeys(values))

                if min_items and len(values) < min_items:
                    print(f"❌ Minimum {min_items} items required")
                    continue

                if max_items and len(values) > max_items:
                    print(f"❌ Maximum {max_items} items allowed")
                    continue

                array_errors = self._validate_array_partial(
                    field_name=field_name,
                    values=values,
                    partial_data=partial_data,
                )
                if array_errors:
                    for e in array_errors:
                        print(f"❌ {e}")
                    continue

                return values

        # Free array
        values = []
        print("Add items one by one (Enter to finish):")

        while True:
            text = self._prompt("> ").strip()
            if not text:
                break

            try:
                value = self._cast_value(text, items.get("type", "string"))
            except ValueError as e:
                print(f"❌ {e}")
                continue

            # Validate item against items schema
            item_errors = self._validate_array_item(value, items)
            if item_errors:
                for e in item_errors:
                    print(f"❌ {e}")
                continue

            # Unique check
            if unique and value in values:
                print("❌ Duplicate value not allowed")
                continue

            # Validate array partially in incremental context
            candidate = values + [value]
            array_errors = self._validate_array_partial(
                field_name=field_name,
                values=candidate,
                partial_data=partial_data,
            )
            if array_errors:
                for e in array_errors:
                    print(f"❌ {e}")
                continue

            values.append(value)

            if max_items and len(values) >= max_items:
                print(f"ℹ Reached maxItems={max_items}")
                break

        if (required or min_items > 0) and len(values) == 0:
            print("❌ At least one value is required")
            return self._ask_array(label, spec, required, field_name, partial_data)

        if min_items and len(values) < min_items:
            print(f"❌ Minimum {min_items} items required")
            return self._ask_array(label, spec, required, field_name, partial_data)

        if max_items and len(values) > max_items:
            print(f"❌ Maximum {max_items} items allowed")
            return self._ask_array(label, spec, required, field_name, partial_data)

        return values

    # ============================================================

    def _cast_value(self, raw: str, field_type: str):
        """Convert a raw string to the Python type indicated by *field_type*.

        Args:
            raw: The string entered by the user.
            field_type: JSON Schema type (``"string"``, ``"integer"``,
                ``"number"`` or ``"boolean"``).

        Returns:
            The converted value.

        Raises:
            ValueError: If the conversion fails or the type is unsupported.
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
        raise ValueError(f"Unsupported field type: {field_type}")

    def _validate_array_item(self, item_value, item_schema) -> list[str]:
        """Validate a single array element against the ``items`` sub-schema.

        Args:
            item_value: The value to validate.
            item_schema: The JSON Schema for array items.

        Returns:
            A list of error messages (empty on success).
        """
        validator = Draft202012Validator(item_schema)
        errors = list(validator.iter_errors(item_value))
        return [e.message for e in errors]

    def _validate_array_partial(
        self,
        field_name: str,
        values: list,
        partial_data: dict,
    ) -> list[str]:
        """Validate the full array in the incremental context.

        Delegates to :meth:`_validate_field_incremental` so that cross-field
        constraints (``minItems``, ``uniqueItems``, ``contains``, etc.) are
        checked.

        Args:
            field_name: Name of the array field.
            values: Current list of collected values.
            partial_data: Previously collected field values.

        Returns:
            A list of error messages (empty on success).
        """
        return self._validate_field_incremental(
            field_name=field_name,
            candidate_value=values,
            partial_data=partial_data,
        )
