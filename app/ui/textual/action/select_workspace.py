from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from pathlib import Path

from app.ui.textual.path_dialog import PathDialog
from app.config import AppConfig, default_workspaces_dir
from app.context.workspace import Workspace


class SelectWorkspace:
    def __init__(self, window: App):
        self.window = window

    async def run(self):
        app_config = AppConfig.load()

        initial_dir = default_workspaces_dir()
        initial_dir.mkdir(parents=True, exist_ok=True)

        result = await self.window.push_screen_wait(
            PathDialog(
                root_dir=Path.home(),
                mode="read",
                select="dir",
                initial_path=initial_dir,
                title="Select workspace directory",
            )
        )

        if result is None:
            self.window.echo(Markdown("No workspace selected."))
            return

        try:
            ws = Workspace.load_or_create(result)
        except Exception as e:
            self.window.echo(Markdown(f"Cannot create workspace: {e}"))
            return

        self.window.current_workspace = ws
        app_config.set_active_workspace(result)
        app_config.save()

        self.window.echo(Markdown(f"Workspace activo: **{ws.name}**"))
