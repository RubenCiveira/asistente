from __future__ import annotations

from textual.app import App
from textual.widgets import Markdown

from pathlib import Path

from app.ui.textual.path_dialog import PathDialog
from app.ui.textual.form import FormDialog
from app.ui.textual.confirm import Confirm
from app.context.project import Project

_NEW_PROJECT = "__new__"


class SelectProject:
    def __init__(self, window):
        self.window = window

    async def run(self):
        ws = self.window.get_active_workspace()
        if ws is None:
            self.window.echo(Markdown("Error: no hay workspace seleccionado."))
            return

        prj = await self.select_project(ws)
        if prj is not None:
            self.window.select_project(prj)

    async def select_project(self, ws):
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
            result = await self.window.push_screen_wait(FormDialog(schema))
            if result is None:
                return None
            chosen = result["project"]
            if chosen != _NEW_PROJECT:
                try:
                    return Project.load_or_create(path_by_key[chosen])
                except Exception as e:
                    self.window.echo(Markdown(f"Cannot load project: {e}"))
                    return None

        return await self.new_project()

    async def new_project(self):
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
            return Project.load_or_create(result)
        except Exception as e:
            self.window.echo(Markdown(f"Cannot create project: {e}"))
            return None
