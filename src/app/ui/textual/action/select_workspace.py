"""TUI action for selecting or creating a workspace, followed by project selection.

Presents a list of recently used workspaces or lets the user browse for a
new directory.  After a workspace is chosen the companion
:class:`~app.ui.textual.action.select_project.SelectProject` action runs
automatically.
"""

from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from pathlib import Path

from app.ui.textual.widgets.path_dialog import PathDialog
from app.ui.textual.widgets.form import FormDialog
from app.config import AppConfig, default_workspaces_dir
from app.context.workspace import Workspace

from app.ui.textual.action.select_project import SelectProject

_NEW_WORKSPACE = "__new__"


class SelectWorkspace:
    """Action that guides the user through picking or creating a workspace.

    After a workspace is selected the *select_project* action is invoked
    so the user can immediately choose a project inside the workspace.

    Args:
        window: The main application instance.
        select_project: A :class:`SelectProject` action to chain after
            workspace selection.
    """

    def __init__(self, window, select_project: SelectProject):
        self.window = window
        self.select_project = select_project

    async def run(self):
        """Execute the full workspace-then-project selection flow."""
        ws = await self.select_workspace()
        if ws is None:
            self.window.echo(Markdown("No workspace selected."))
            return
        self.window.select_workspace(ws)
        await self.select_project.run()

    async def select_workspace(self):
        """Show a form listing recent workspaces or create a new one.

        Returns:
            A :class:`~app.context.workspace.Workspace` or ``None`` on cancel.
        """
        recent = self.window.config.recent_workspaces or []

        if recent:
            path_by_key = {f"ws-{i}": p for i, p in enumerate(recent)}
            options = [
                {"const": key, "title": p.name}
                for key, p in path_by_key.items()
            ] + [
                {"const": _NEW_WORKSPACE, "title": "Otro directorio..."}
            ]
            schema = {
                "type": "object",
                "properties": {
                    "workspace": {
                        "type": "string",
                        "description": "Selecciona un workspace",
                        "oneOf": options,
                    }
                },
                "required": ["workspace"],
            }
            result = await self.window.push_screen_wait(FormDialog(schema))
            if result is None:
                return None
            chosen = result["workspace"]
            if chosen != _NEW_WORKSPACE:
                try:
                    return Workspace.load_or_create(path_by_key[chosen], valid_topics=self.window.config.topic_names())
                except Exception as e:
                    self.window.echo(Markdown(f"Cannot load workspace: {e}"))
                    return None
            ws = await self.new_worksapce()
            return ws
        return None

    async def new_worksapce(self):
        """Open a :class:`PathDialog` for the user to pick a new workspace directory.

        Returns:
            A :class:`~app.context.workspace.Workspace` or ``None`` on cancel.
        """
        initial_dir = default_workspaces_dir()
        initial_dir.mkdir(parents=True, exist_ok=True)
        result = await self.window.push_screen_wait(
            PathDialog(
                root_dir=Path.home(),
                must_exist=False,
                select="dir",
                initial_path=initial_dir,
                title="Select workspace directory",
            )
        )
        if result is None:
            return None
        try:
            return Workspace.load_or_create(result, valid_topics=self.window.config.topic_names())
        except Exception as e:
            self.window.echo(Markdown(f"Cannot create workspace: {e}"))
            return
