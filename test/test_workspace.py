"""Tests for app.context.workspace.Workspace."""

from __future__ import annotations

import json
from pathlib import Path

from app.context.workspace import Workspace


class TestWorkspaceLoadOrCreate:
    def test_creates_new_workspace(self, tmp_path):
        d = tmp_path / "ws"
        ws = Workspace.load_or_create(d)
        assert ws.name == "ws"
        assert d.exists()
        assert (d / "workspace.json").exists()

    def test_reload_preserves_name(self, tmp_path):
        d = tmp_path / "ws"
        ws1 = Workspace.load_or_create(d)
        ws2 = Workspace.load_or_create(d)
        assert ws1.name == ws2.name

    def test_creates_directory_if_missing(self, tmp_path):
        d = tmp_path / "deep" / "nested" / "ws"
        ws = Workspace.load_or_create(d)
        assert d.exists()
        assert ws.root_dir == d

    def test_default_projects_empty(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        assert ws.projects == []

    def test_default_active_project_none(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        assert ws.active_project is None


class TestWorkspaceAddProject:
    def test_add_project(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        prj_dir = tmp_path / "proj1"
        prj_dir.mkdir()
        ws.add_project(prj_dir)
        assert prj_dir.resolve() in ws.projects

    def test_add_duplicate_ignored(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        prj_dir = tmp_path / "proj1"
        prj_dir.mkdir()
        ws.add_project(prj_dir)
        ws.add_project(prj_dir)
        assert ws.projects.count(prj_dir.resolve()) == 1

    def test_add_project_persists(self, tmp_path):
        ws_dir = tmp_path / "ws"
        ws = Workspace.load_or_create(ws_dir)
        prj_dir = tmp_path / "proj1"
        prj_dir.mkdir()
        ws.add_project(prj_dir)
        ws2 = Workspace.load_or_create(ws_dir)
        assert prj_dir.resolve() in ws2.projects


class TestWorkspaceSetActiveProject:
    def test_sets_active_and_adds(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        prj_dir = tmp_path / "proj1"
        prj_dir.mkdir()
        ws.set_active_project(prj_dir)
        assert ws.active_project == prj_dir.resolve()
        assert prj_dir.resolve() in ws.projects


class TestWorkspaceFile:
    def test_file_property(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        assert ws.file == tmp_path / "ws" / "workspace.json"


class TestWorkspaceSave:
    def test_save_writes_json(self, tmp_path):
        ws_dir = tmp_path / "ws"
        ws = Workspace.load_or_create(ws_dir)
        ws.name = "custom"
        ws.save()
        data = json.loads((ws_dir / "workspace.json").read_text())
        assert data["name"] == "custom"
