"""Tests for app.ui.textual.action.select_project.SelectProject."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.ui.textual.action.select_project import SelectProject
from app.context.project import Project
from app.context.workspace import Workspace


def _make_window(workspace=None):
    """Create a mock window with optional workspace."""
    window = MagicMock()
    window.get_active_workspace.return_value = workspace
    window.echo = MagicMock()
    window.select_project = MagicMock()
    window.push_screen_wait = AsyncMock(return_value=None)
    return window


class TestSelectProjectRun:
    @pytest.mark.asyncio
    async def test_no_workspace_shows_error(self):
        window = _make_window(workspace=None)
        action = SelectProject(window)
        await action.run()
        window.echo.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_workspace_calls_select_project(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        prj_dir = tmp_path / "proj"
        prj = Project.load_or_create(prj_dir)

        window = _make_window(workspace=ws)
        action = SelectProject(window)

        with patch.object(action, "select_project", new_callable=AsyncMock, return_value=prj):
            await action.run()
        window.select_project.assert_called_once_with(prj)

    @pytest.mark.asyncio
    async def test_cancel_does_not_select(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        window = _make_window(workspace=ws)
        action = SelectProject(window)

        with patch.object(action, "select_project", new_callable=AsyncMock, return_value=None):
            await action.run()
        window.select_project.assert_not_called()


class TestSelectProjectMethod:
    @pytest.mark.asyncio
    async def test_no_projects_goes_to_new(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        window = _make_window(workspace=ws)
        action = SelectProject(window)

        with patch.object(action, "new_project", new_callable=AsyncMock, return_value=None):
            result = await action.select_project(ws)
        assert result is None
