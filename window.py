from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work

from app.textual.form import FormDialog

class MainApp(App):
    CSS = """
    #chat {
        height: 1fr;
        border: round $primary;
        padding: 1 2;
        overflow-y: auto;
    }

    #prompt {
        border: round $accent;
    }
    """

    @work
    async def open_form_worker(self):
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

        result = await self.push_screen_wait(FormDialog(schema, initial_values))
        self._handle_form_result(result)

    def _handle_form_result(self, result):
        chat = self.query_one("#chat", VerticalScroll)
        if result is None:
            chat.mount(Markdown("Formulario cancelado."))
        else:
            chat.mount(Markdown(str(result)))
        chat.scroll_end(animate=False)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with VerticalScroll(id="chat"):
                yield Markdown("Listo. Aquí irá el chat/log en **Markdown**.")
            with Horizontal():
                yield Button("Open Form", id="open_form", variant="primary")
                yield Button("Clear", id="clear_chat")
            yield Input(placeholder="Escribe aquí… (Enter para enviar)", id="prompt")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "clear_chat":
            chat = self.query_one("#chat", VerticalScroll)
            chat.remove_children()

        if event.button.id == "open_form":
            self.open_form_worker()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "prompt":
            return
        text = event.value.strip()
        if not text:
            return
        chat = self.query_one("#chat", VerticalScroll)
        chat.mount(Markdown(f"**user>** {text}"))
        chat.scroll_end(animate=False)
        event.input.value = ""


if __name__ == "__main__":
    MainApp().run()
