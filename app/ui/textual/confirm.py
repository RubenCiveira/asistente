from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

class Confirm(ModalScreen[bool]):
    DEFAULT_CSS = """
    Confirm {
        align: center middle;
        background: $surface 80%;
    }

    #dialog {
        width: 60%;
        max-width: 80;
        min-width: 40;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #title { text-style: bold; margin-bottom: 1; }
    #subtitle { margin-bottom: 1; }
    #buttons { margin-top: 1; align: right middle; height: auto; }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        title: str = "Confirm",
        subtitle: str = "",
        ok_text: str = "OK",
        cancel_text: str = "Cancel",
    ):
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self._ok_text = ok_text
        self._cancel_text = cancel_text

    def compose(self):
        with Vertical(id="dialog"):
            yield Static(self._title, id="title")
            if self._subtitle:
                yield Static(self._subtitle, id="subtitle")
            with Horizontal(id="buttons"):
                yield Button(self._cancel_text, id="cancel", variant="default")
                yield Button(self._ok_text, id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "ok")

    def action_cancel(self) -> None:
        self.dismiss(False)
