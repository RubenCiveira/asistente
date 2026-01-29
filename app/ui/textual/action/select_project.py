from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from pathlib import Path

from app.ui.textual.path_dialog import PathDialog
from app.config import AppConfig, default_workspaces_dir
from app.context.project import Project

class SelectProject:
    def __init__(self, window):
        self.window = window

    async def run(self):
        result = await self.window.push_screen_wait(
            PathDialog(
                root_dir=Path.home(),
                must_exist=False,
                select="dir",
                title="Select project directory",
            )
        )

        if result is None:
            self.window.echo(Markdown("No workspace selected."))
            return
    
        try:
            prj = Project.load_from_dir(result)
            self.window.select_project(prj)
        except Exception as e:
            self.window.echo(Markdown(f"Cannot create workspace: {e}"))
            return
