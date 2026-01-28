from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
from textual.containers import Vertical
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


    async def on_mount(self):
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
        result = await self.push_screen(FormDialog(schema))
        chat = self.query_one("#chat", Static)
        if result is None:
            chat.update("Formulario cancelado.")
        else:
            chat.update(str(result))

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Listo. Aquí irá el chat/log.", id="chat")
            yield Input(placeholder="Escribe aquí… (Enter para enviar)", id="prompt")
        yield Footer()

    # def on_input_submitted(self, event: Input.Submitted) -> None:
    #     chat = self.query_one("#chat", Static)
    #     text = event.value.strip()
    #     if not text:
    #         return

    #     # “log” simple: añadimos líneas (luego lo haremos bonito)
    #     chat.update(chat.renderable + f"\n\n[b]user>[/b] {text}")
    #     event.input.value = ""


if __name__ == "__main__":
    MainApp().run()
