"""Generic report modal for Textual applications.

Displays a centered dialog with a title, a message, optional exception details,
and a single acknowledgment button.
"""

from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal


class Report(ModalScreen[None]):
    """Modal report dialog.

    Args:
        message: Main text displayed in the dialog body.
        level: Severity label used for the title (e.g., info, warning, error).
            If omitted, defaults to "error" when exception is provided,
            otherwise "info".
        exception: Optional exception to show details from.
        title: Optional custom title. Defaults to the level title-cased.
        ok_text: Label for the acknowledgment button.
    """

    DEFAULT_CSS = """
    Report {
        align: center middle;
        background: $surface 80%;
    }

    #dialog {
        width: 70%;
        max-width: 90;
        min-width: 40;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #title { text-style: bold; margin-bottom: 1; }
    #message { margin-bottom: 1; }
    #exception { text-style: italic; }
    #buttons { margin-top: 1; align: right middle; height: auto; }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(
        self,
        message: str = "",
        level: str | None = None,
        exception: Exception | None = None,
        title: str | None = None,
        ok_text: str = "OK",
    ) -> None:
        super().__init__()
        resolved_level = (level or ("error" if exception else "info")).lower()
        if not message and exception is not None:
            message = str(exception) or "An error occurred."
        if not message:
            message = "No details provided."

        self._message = message
        self._level = resolved_level
        self._exception = exception
        self._title = title or resolved_level.title()
        self._ok_text = ok_text

    def compose(self):
        """Build the dialog widget tree."""
        with Vertical(id="dialog"):
            yield Static(self._title, id="title")
            yield Static(self._message, id="message")
            if self._exception is not None:
                exception_label = self._exception.__class__.__name__
                exception_text = str(self._exception).strip()
                details = exception_label
                if exception_text:
                    details = f"{exception_label}: {exception_text}"
                yield Static(details, id="exception")
            with Horizontal(id="buttons"):
                yield Button(self._ok_text, id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dismiss the dialog."""
        if event.button.id == "ok":
            self.dismiss(None)

    def action_close(self) -> None:
        """Handle the Escape key by dismissing."""
        self.dismiss(None)
