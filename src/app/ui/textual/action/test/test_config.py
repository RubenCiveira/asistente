"""Manual TUI smoke test for ConfigDialog.

This is **not** a pytest test.  It is an interactive action class that can
be wired into the running TUI to exercise :class:`ConfigDialog` with a
multi-page hierarchical configuration including various field types.
"""

from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from app.ui.textual.widgets.config_dialog import (
    ConfigDialog,
    ConfigPage,
    ConfigValues,
)


class TestConfig:
    """Interactive demo action that opens a :class:`ConfigDialog` and echoes the result.

    Args:
        window: The main application instance.
    """

    def __init__(self, window: App):
        self.window = window

    async def run(self):
        """Show a ConfigDialog with sample pages and display the result."""
        pages = [
            ConfigPage(
                id="general",
                title="General",
                schema={
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "enum": ["es", "en", "pt"],
                            "default": "es",
                            "description": "Idioma de la interfaz",
                        },
                        "username": {
                            "type": "string",
                            "description": "Nombre de usuario",
                            "minLength": 1,
                            "maxLength": 50,
                        },
                        "notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Activar notificaciones",
                        },
                    },
                    "required": ["username"],
                },
                children=[
                    ConfigPage(
                        id="advanced",
                        title="Advanced",
                        schema={
                            "type": "object",
                            "properties": {
                                "log_level": {
                                    "oneOf": [
                                        {"const": "debug", "title": "Debug"},
                                        {"const": "info", "title": "Info"},
                                        {"const": "warning", "title": "Warning"},
                                        {"const": "error", "title": "Error"},
                                    ],
                                    "default": "info",
                                    "description": "Nivel de log",
                                },
                                "max_retries": {
                                    "type": "integer",
                                    "default": 3,
                                    "minimum": 0,
                                    "maximum": 10,
                                    "description": "Reintentos maximos",
                                },
                            },
                        },
                    ),
                ],
            ),
            ConfigPage(
                id="editor",
                title="Editor",
                schema={
                    "type": "object",
                    "properties": {
                        "font_size": {
                            "type": "integer",
                            "default": 14,
                            "minimum": 8,
                            "maximum": 72,
                            "description": "Tamano de fuente",
                        },
                        "theme": {
                            "type": "string",
                            "enum": ["light", "dark", "solarized"],
                            "default": "dark",
                            "description": "Tema del editor",
                        },
                        "plugins": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"const": "lint", "title": "Linting"},
                                    {"const": "format", "title": "Auto-format"},
                                    {"const": "git", "title": "Git integration"},
                                    {"const": "ai", "title": "AI assist"},
                                ],
                            },
                            "description": "Plugins activos",
                        },
                    },
                },
            ),
            ConfigPage(
                id="paths",
                title="Paths",
                schema={
                    "type": "object",
                    "properties": {
                        "search_dirs": {
                            "type": "array",
                            "description": "Directorios de busqueda",
                            "items": {
                                "type": "string",
                                "minLength": 1,
                            },
                        },
                    },
                },
            ),
        ]

        initial = {
            "general": ConfigValues(
                values={
                    "language": "es",
                    "username": "ruben",
                    "notifications": True,
                },
                childs={
                    "advanced": ConfigValues(
                        values={"log_level": "info", "max_retries": 3},
                    ),
                },
            ),
            "editor": ConfigValues(
                values={
                    "font_size": 14,
                    "theme": "dark",
                    "plugins": ["lint", "git"],
                },
            ),
            "paths": ConfigValues(
                values={
                    "search_dirs": ["src", "tests", "docs"],
                },
            ),
        }

        result = await self.window.push_screen_wait(
            ConfigDialog(pages, initial_values=initial)
        )

        if result is None:
            self.window.echo(Markdown("Configuracion cancelada."))
        else:
            lines = ["**Configuracion guardada:**\n"]
            for page_id, cv in result.items():
                lines.append(f"- **{page_id}**: `{cv.values}`")
                for child_id, child_cv in cv.childs.items():
                    lines.append(f"  - **{child_id}**: `{child_cv.values}`")
            self.window.echo(Markdown("\n".join(lines)))
