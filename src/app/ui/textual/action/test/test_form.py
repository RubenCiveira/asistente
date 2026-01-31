"""Manual TUI smoke test for WizardFromSchema.

This is **not** a pytest test.  It is an interactive action class that can
be wired into the running TUI to exercise :class:`WizardFromSchema` with a
complex JSON Schema including cross-field validation.
"""

from __future__ import annotations

from typing import Any, cast

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work

from pathlib import Path
from app.ui.textual.widgets.wizard_from_schema import WizardFromSchema
from app.ui.textual.widgets.path_dialog import PathDialog

from app.config import AppConfig, default_workspaces_dir


class TestForm:
    """Interactive demo action that opens a :class:`WizardFromSchema` with a rich schema.

    Args:
        window: The main application instance.
    """

    def __init__(self, window: App):
        self.window = window

    async def run(self):
        """Show a WizardFromSchema with a comprehensive test schema and echo the result."""
        schema = {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "description": "Directorios a analizar",
                    "minItems": 1,
                    "maxItems": 10,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                        # path "simple": evita espacios raros; permite / . _ - letras números
                        "pattern": r"^[a-zA-Z0-9._/\-]+$",
                    },
                },
                "repo_url": {
                    "type": "string",
                    "description": "Git repository URL (https://... o git@...)",
                    # Valida URLs tipo http(s) y ssh (simplificado)
                    "pattern": r"^(https?://|git@).+",
                    "minLength": 8,
                    "maxLength": 300,
                },
                "lang": {
                    "type": "string",
                    "enum": ["es", "en"],
                    "default": "es",
                    "description": "Idioma principal",
                },
                "mode": {
                    "oneOf": [
                        {"const": "generic", "title": "Uso general"},
                        {"const": "coding", "title": "Programación"},
                        {"const": "reasoning", "title": "Razonamiento"},
                    ],
                    "default": "generic",
                },
                "features": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"const": "lint", "title": "Linting"},
                            {"const": "tests", "title": "Tests"},
                            {"const": "docs", "title": "Documentación"},
                        ]
                    },
                    "minItems": 1,
                    "maxItems": 3,
                    "uniqueItems": True,
                },
                "branch": {
                    "type": "string",
                    "default": "main",
                    # muy simplificado pero útil: evita espacios y caracteres peligrosos
                    "pattern": r"^[A-Za-z0-9._/\-]+$",
                    "minLength": 1,
                    "maxLength": 120,
                },
                "private": {
                    "type": "boolean",
                    "default": False,
                },
                "repo_token": {
                    "type": "string",
                    "description": "Token de acceso si el repo es privado",
                    "minLength": 10,
                    "maxLength": 200,
                },
                "depth": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["repo_url"],

            # --------------------------
            # Validación cruzada (pro)
            # --------------------------
            "allOf": [
                # Si private=true, exigir repo_token
                {
                    "if": {
                        "properties": {"private": {"const": True}},
                        "required": ["private"],
                    },
                    "then": {"required": ["repo_token"]},
                },

                # Si mode=coding, exigir que features contenga "tests"
                # (JSON Schema 2020-12: contains)
                {
                    "if": {
                        "properties": {"mode": {"const": "coding"}},
                        "required": ["mode"],
                    },
                    "then": {
                        "properties": {
                            "features": {
                                "contains": {"const": "tests"}
                            }
                        }
                    },
                },

                # Ejemplo de restricción: si lang=en, no permitir mode=reasoning
                {
                    "if": {
                        "properties": {"lang": {"const": "en"}},
                        "required": ["lang"],
                    },
                    "then": {
                        "not": {
                            "properties": {"mode": {"const": "reasoning"}},
                            "required": ["mode"],
                        }
                    },
                },
            ],
        }
        initial_values = {
            "repo_url": "https://github.com/tu-org/tu-repo",
            "paths": ["src", "tests"],
            "lang": "es",
            "mode": "coding",
            "features": ["tests", "lint"],
            "branch": "main",
            "private": False,
            "depth": 3,
        }

        result = await self.window.push_screen_wait(WizardFromSchema(schema, initial_values))
        
        window = cast(Any, self.window)
        if result is None:
            window.echo(Markdown("Formulario cancelado."))
        else:
            window.echo(Markdown(str(result)))
