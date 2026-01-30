"""Tests for app.ui.textual.action.select_workspace.SelectWorkspace."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.ui.textual.action.select_workspace import SelectWorkspace
from app.ui.textual.action.select_project import SelectProject
from app.context.workspace import Workspace


def _make_window():
    """Create a mock window."""
    window = MagicMock()
    window.echo = MagicMock()
    window.select_workspace = MagicMock()
    window.push_screen_wait = AsyncMock(return_value=None)
    window.config = MagicMock()
    window.config.recent_workspaces = []
    return window


class TestSelectWorkspaceRun:
    @pytest.mark.asyncio
    async def test_no_workspace_selected_shows_message(self):
        window = _make_window()
        sp = SelectProject(window)
        action = SelectWorkspace(window, sp)

        with patch.object(action, "select_workspace", new_callable=AsyncMock, return_value=None):
            await action.run()
        window.echo.assert_called_once()

    @pytest.mark.asyncio
    async def test_workspace_selected_chains_to_project(self, tmp_path):
        ws = Workspace.load_or_create(tmp_path / "ws")
        window = _make_window()
        sp = SelectProject(window)
        action = SelectWorkspace(window, sp)

        with patch.object(action, "select_workspace", new_callable=AsyncMock, return_value=ws):
            with patch.object(sp, "run", new_callable=AsyncMock) as mock_run:
                await action.run()
        window.select_workspace.assert_called_once_with(ws)
        mock_run.assert_called_once()


class TestSelectWorkspaceMethod:
    @pytest.mark.asyncio
    async def test_no_recent_returns_none(self):
        window = _make_window()
        sp = SelectProject(window)
        action = SelectWorkspace(window, sp)
        result = await action.select_workspace()
        assert result is None
