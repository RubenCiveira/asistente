"""Simple yes/no confirmation modal for Textual applications.

Displays a centred dialog with a title, optional subtitle and two buttons
(OK / Cancel).  Dismisses with ``True`` when the user confirms or ``False``
when the user cancels (button or Escape key).
"""

from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal


class Confirm(ModalScreen[bool]):
    """Modal confirmation dialog.

    Args:
        title: Heading displayed at the top of the dialog.
        subtitle: Optional secondary text shown below the title.
        ok_text: Label for the confirmation button.
        cancel_text: Label for the cancellation button.
    """

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
    ) -> None:
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self._ok_text = ok_text
        self._cancel_text = cancel_text

    def compose(self):
        """Build the dialog widget tree."""
        with Vertical(id="dialog"):
            yield Static(self._title, id="title")
            if self._subtitle:
                yield Static(self._subtitle, id="subtitle")
            with Horizontal(id="buttons"):
                yield Button(self._cancel_text, id="cancel", variant="default")
                yield Button(self._ok_text, id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss with ``True`` for OK, ``False`` for Cancel."""
        self.dismiss(event.button.id == "ok")

    def action_cancel(self) -> None:
        """Handle the Escape key by dismissing with ``False``."""
        self.dismiss(False)
