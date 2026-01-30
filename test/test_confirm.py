"""Tests for app.ui.textual.confirm.Confirm."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from app.ui.textual.confirm import Confirm


class ConfirmApp(App):
    """Thin wrapper to push a Confirm dialog in tests."""

    RESULT = "_UNSET"

    def __init__(self, **kwargs):
        super().__init__()
        self._kwargs = kwargs
        ConfirmApp.RESULT = "_UNSET"

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            Confirm(**self._kwargs),
            callback=self._on_result,
        )

    def _on_result(self, result):
        ConfirmApp.RESULT = result
        self.exit()


class TestConfirm:
    @pytest.mark.asyncio
    async def test_ok_returns_true(self):
        app = ConfirmApp(title="Delete?", ok_text="Yes", cancel_text="No")
        async with app.run_test() as pilot:
            await pilot.click("#ok")
        assert ConfirmApp.RESULT is True

    @pytest.mark.asyncio
    async def test_cancel_returns_false(self):
        app = ConfirmApp(title="Delete?")
        async with app.run_test() as pilot:
            await pilot.click("#cancel")
        assert ConfirmApp.RESULT is False

    @pytest.mark.asyncio
    async def test_escape_returns_false(self):
        app = ConfirmApp(title="Delete?")
        async with app.run_test() as pilot:
            await pilot.press("escape")
        assert ConfirmApp.RESULT is False

    @pytest.mark.asyncio
    async def test_custom_button_labels(self):
        app = ConfirmApp(title="T", ok_text="Proceed", cancel_text="Abort")
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            ok_btn = dialog.query_one("#ok", Button)
            cancel_btn = dialog.query_one("#cancel", Button)
            assert str(ok_btn.label) == "Proceed"
            assert str(cancel_btn.label) == "Abort"
            await pilot.click("#cancel")

    @pytest.mark.asyncio
    async def test_subtitle_shown(self):
        app = ConfirmApp(title="Title", subtitle="Sub text")
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            subtitle = dialog.query_one("#subtitle")
            assert subtitle is not None
            await pilot.click("#cancel")
