"""Tests for app.ui.textual.path_dialog.PathDialog."""

from __future__ import annotations

import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Button, Input

from app.ui.textual.path_dialog import PathDialog


class PathApp(App):
    """Thin wrapper to push a PathDialog in tests."""

    RESULT = "_UNSET"

    def __init__(self, **kwargs):
        super().__init__()
        self._kwargs = kwargs
        PathApp.RESULT = "_UNSET"

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            PathDialog(**self._kwargs),
            callback=self._on_result,
        )

    def _on_result(self, result):
        PathApp.RESULT = result
        self.exit()


class TestPathDialogCancel:
    @pytest.mark.asyncio
    async def test_cancel_button_returns_none(self, tmp_path):
        app = PathApp(root_dir=tmp_path)
        async with app.run_test() as pilot:
            await pilot.click("#btn_cancel")
        assert PathApp.RESULT is None

    @pytest.mark.asyncio
    async def test_escape_returns_none(self, tmp_path):
        app = PathApp(root_dir=tmp_path)
        async with app.run_test() as pilot:
            await pilot.press("escape")
        assert PathApp.RESULT is None


class TestPathDialogValidation:
    @pytest.mark.asyncio
    async def test_must_exist_rejects_missing(self, tmp_path):
        app = PathApp(root_dir=tmp_path, must_exist=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            inp = dialog.query_one("#path_input", Input)
            inp.value = "/nonexistent"
            await pilot.click("#btn_ok")
            await pilot.pause()
            # Dialog should still be open (error shown)
            assert PathApp.RESULT == "_UNSET"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_select_existing_dir(self, tmp_path):
        subdir = tmp_path / "mydir"
        subdir.mkdir()
        app = PathApp(root_dir=tmp_path, must_exist=True, select="dir")
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            inp = dialog.query_one("#path_input", Input)
            inp.value = "/mydir"
            await pilot.click("#btn_ok")
        assert PathApp.RESULT == subdir

    @pytest.mark.asyncio
    async def test_initial_path_shown(self, tmp_path):
        subdir = tmp_path / "init"
        subdir.mkdir()
        app = PathApp(root_dir=tmp_path, must_exist=False, initial_path=subdir)
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            inp = dialog.query_one("#path_input", Input)
            assert "init" in inp.value
            await pilot.press("escape")
