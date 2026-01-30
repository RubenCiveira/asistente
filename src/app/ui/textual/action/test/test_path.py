"""Manual TUI smoke test for PathDialog.

This is **not** a pytest test.  It is an interactive action class that can
be wired into the running TUI to exercise :class:`PathDialog`.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work

from pathlib import Path
from app.ui.textual.widgets.form import FormDialog
from app.ui.textual.widgets.path_dialog import PathDialog

from app.config import AppConfig, default_workspaces_dir


class TestPath:
    """Interactive demo action that opens a :class:`PathDialog` and echoes the result.

    Args:
        window: The main application instance.
    """

    def __init__(self, window: App):
        self.window = window

    async def run(self):
        """Show a PathDialog and display the selected path."""
        result = await self.window.push_screen_wait(
            PathDialog(
                root_dir=Path("/Users/ruben.civeiraiglesia/"),
                sub_title="Búsqueda preparada"
            )
        )
        if result is None:
            self.window.echo( Markdown("No se ha escogido fichero") )
        else:
            self.window.echo( Markdown(str(result)) )