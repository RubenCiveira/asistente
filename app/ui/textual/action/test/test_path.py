from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work

from pathlib import Path
from app.ui.textual.form import FormDialog
from app.ui.textual.path_dialog import PathDialog

from app.config import AppConfig, default_workspaces_dir

class TestPath:
    def __init__(self, window: App):
        self.window = window

    async def run(self):
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