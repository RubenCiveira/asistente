"""TUI action for selecting or creating a project within the active workspace.

Presents the user with a list of known projects (if any) or jumps straight
to the new-project flow via :class:`~app.ui.textual.widgets.path_dialog.PathDialog`.
"""

from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from pathlib import Path

from app.ui.textual.widgets.path_dialog import PathDialog
from app.ui.textual.widgets.wizard_from_schema import WizardFromSchema
from app.ui.textual.widgets.confirm import Confirm
from app.context.project import Project

_NEW_PROJECT = "__new__"


class SelectProject:
    """Action that guides the user through picking or creating a project.

    Args:
        window: The main application instance (provides ``push_screen_wait``,
            ``echo``, ``get_active_workspace`` and ``select_project``).
    """

    def __init__(self, window):
        self.window = window

    async def run(self):
        """Execute the full project-selection flow.

        Shows an error if no workspace is active; otherwise delegates to
        :meth:`select_project` and applies the result.
        """
        ws = self.window.get_active_workspace()
        if ws is None:
            self.window.echo(Markdown("Error: no hay workspace seleccionado."))
            return

        prj = await self.select_project(ws)
        if prj is not None:
            self.window.select_project(prj)

    async def select_project(self, ws):
        """Show a form with existing projects or fall through to :meth:`new_project`.

        Args:
            ws: The active :class:`~app.context.workspace.Workspace`.

        Returns:
            A :class:`~app.context.project.Project` or ``None`` on cancel.
        """
        projects = ws.projects or []

        if projects:
            path_by_key = {f"prj-{i}": p for i, p in enumerate(projects)}
            options = [
                {"const": key, "title": p.name}
                for key, p in path_by_key.items()
            ] + [
                {"const": _NEW_PROJECT, "title": "Otro directorio..."}
            ]
            schema = {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Selecciona un proyecto",
                        "oneOf": options,
                    }
                },
                "required": ["project"],
            }
            result = await self.window.push_screen_wait(WizardFromSchema(schema))
            if result is None:
                return None
            chosen = result["project"]
            if chosen != _NEW_PROJECT:
                try:
                    return Project.load_or_create(path_by_key[chosen], valid_topics=self.window.config.topic_names())
                except Exception as e:
                    self.window.echo(Markdown(f"Cannot load project: {e}"))
                    return None

        return await self.new_project()

    async def new_project(self):
        """Open a :class:`PathDialog` for the user to pick a new project directory.

        If the chosen directory does not exist a confirmation dialog is shown
        before creating it.

        Returns:
            A :class:`~app.context.project.Project` or ``None`` on cancel.
        """
        result = await self.window.push_screen_wait(
            PathDialog(
                root_dir=Path.home(),
                must_exist=False,
                select="dir",
                title="Select project directory",
            )
        )
        if result is None:
            return None
        if not result.exists():
            confirmed = await self.window.push_screen_wait( Confirm(
                title="No existe el directorio",
                subtitle="Vamos a crear el directorio para el proyecto indicado",
                ok_text="Crear directorio",
                cancel_text="Cancelar",
            ))
            if not confirmed:
                result = await self.new_project()
                return result
        try:
            return Project.load_or_create(result, valid_topics=self.window.config.topic_names())
        except Exception as e:
            self.window.echo(Markdown(f"Cannot create project: {e}"))
            return None
