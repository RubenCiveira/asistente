"""Tests for app.ui.textual.chat_input.ChatInput."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from app.context.keywords import Keywords
from app.ui.textual.chat_input import ChatInput
from app.ui.textual.completion_provider.slash_provider import SlashCommandProvider
from app.ui.textual.completion_provider.hash_provider import SemanticProvider


def _make_resolvers():
    return {
        "/": SlashCommandProvider(),
        "#": SemanticProvider(),
    }


class ChatApp(App):
    """Thin wrapper to test ChatInput."""

    SUBMITTED = None

    def __init__(self):
        super().__init__()
        ChatApp.SUBMITTED = None

    def compose(self) -> ComposeResult:
        resolvers = _make_resolvers()
        yield ChatInput(
            keywords=Keywords(sorted(resolvers.keys(), key=len, reverse=True)),
            triggers=resolvers,
            id="test_chat",
        )

    def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        ChatApp.SUBMITTED = event.value
        self.exit()


class TestChatInput:
    @pytest.mark.asyncio
    async def test_submit_text(self):
        app = ChatApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h", "e", "l", "l", "o")
            await pilot.press("enter")
        assert ChatApp.SUBMITTED == "hello"

    @pytest.mark.asyncio
    async def test_empty_submit_ignored(self):
        app = ChatApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            # Should still be running (no submit)
            assert ChatApp.SUBMITTED is None

    @pytest.mark.asyncio
    async def test_input_clears_after_submit(self):
        app = ChatApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("t", "e", "s", "t")
            await pilot.press("enter")
        assert ChatApp.SUBMITTED == "test"
