"""Tests for app.ui.textual.widgets.config_dialog."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Tree

from app.ui.textual.widgets.config_dialog import (
    ConfigDialog,
    ConfigPage,
    ConfigValues,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _simple_pages():
    """Two flat pages, no children."""
    return [
        ConfigPage(
            id="general",
            title="General",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "count": {"type": "integer", "minimum": 1},
                },
                "required": ["name"],
            },
        ),
        ConfigPage(
            id="display",
            title="Display",
            schema={
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark"],
                    },
                },
            },
        ),
    ]


def _nested_pages():
    """One root page with a child."""
    return [
        ConfigPage(
            id="root",
            title="Root",
            schema={
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                },
            },
            children=[
                ConfigPage(
                    id="child",
                    title="Child",
                    schema={
                        "type": "object",
                        "properties": {
                            "level": {"type": "integer"},
                        },
                    },
                ),
            ],
        ),
    ]


# ── Helper apps ───────────────────────────────────────────────────────

class ConfigApp(App):
    """Push ConfigDialog on mount via push_screen + callback."""

    RESULT = "_UNSET"

    def __init__(self, pages, initial=None):
        super().__init__()
        self._pages = pages
        self._initial = initial
        ConfigApp.RESULT = "_UNSET"

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            ConfigDialog(self._pages, initial_values=self._initial),
            callback=self._on_result,
        )

    def _on_result(self, result):
        ConfigApp.RESULT = result
        self.exit()


class ApplyApp(App):
    """App that captures Applied messages without closing."""

    APPLIED_VALUES = None
    DISMISSED = False

    def __init__(self, pages, initial=None):
        super().__init__()
        self._pages = pages
        self._initial = initial
        ApplyApp.APPLIED_VALUES = None
        ApplyApp.DISMISSED = False

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            ConfigDialog(self._pages, initial_values=self._initial),
            callback=self._on_result,
        )

    def _on_result(self, result):
        ApplyApp.DISMISSED = True
        self.exit()

    def on_config_dialog_applied(self, event: ConfigDialog.Applied) -> None:
        ApplyApp.APPLIED_VALUES = event.values


# ── Tests ─────────────────────────────────────────────────────────────

class TestConfigDialog:
    @pytest.mark.asyncio
    async def test_cancel_returns_none(self):
        """Pressing Cancel dismisses with None."""
        app = ConfigApp(_simple_pages())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()
        assert ConfigApp.RESULT is None

    @pytest.mark.asyncio
    async def test_accept_returns_values(self):
        """Pressing Accept returns collected values."""
        initial = {
            "general": ConfigValues(values={"name": "test", "count": 5}),
            "display": ConfigValues(values={"theme": "dark"}),
        }
        app = ConfigApp(_simple_pages(), initial=initial)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        assert ConfigApp.RESULT is not None
        assert isinstance(ConfigApp.RESULT, dict)
        assert "general" in ConfigApp.RESULT
        assert ConfigApp.RESULT["general"].values["name"] == "test"
        assert ConfigApp.RESULT["general"].values["count"] == 5

    @pytest.mark.asyncio
    async def test_initial_values_populate_fields(self):
        """Initial values are loaded into the form and returned on accept."""
        initial = {
            "general": ConfigValues(values={"name": "hello", "count": 3}),
        }
        app = ConfigApp(_simple_pages(), initial=initial)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        assert ConfigApp.RESULT is not None
        assert ConfigApp.RESULT["general"].values["name"] == "hello"

    @pytest.mark.asyncio
    async def test_tree_renders_pages(self):
        """Tree widget shows all top-level pages."""
        app = ConfigApp(_simple_pages())
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            tree = dialog.query_one("#config-tree", Tree)
            assert len(tree.root.children) == 2
            labels = [str(n.label) for n in tree.root.children]
            assert "General" in labels
            assert "Display" in labels
            await pilot.click("#cancel")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_nested_tree(self):
        """Nested pages render as tree children."""
        app = ConfigApp(_nested_pages())
        async with app.run_test() as pilot:
            await pilot.pause()
            dialog = app.screen
            tree = dialog.query_one("#config-tree", Tree)
            root_node = tree.root.children[0]
            assert str(root_node.label) == "Root"
            assert len(root_node.children) == 1
            assert str(root_node.children[0].label) == "Child"
            await pilot.click("#cancel")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_apply_posts_message_and_stays_open(self):
        """Apply posts Applied message without closing the dialog."""
        initial = {
            "general": ConfigValues(values={"name": "applied"}),
        }
        app = ApplyApp(_simple_pages(), initial=initial)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#apply")
            await pilot.pause()
            # Dialog should still be open
            assert ApplyApp.APPLIED_VALUES is not None
            assert "general" in ApplyApp.APPLIED_VALUES
            assert ApplyApp.APPLIED_VALUES["general"].values["name"] == "applied"
            # Dialog has not dismissed yet
            assert ApplyApp.DISMISSED is False
            await pilot.click("#cancel")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_escape_cancels(self):
        """Pressing Escape dismisses with None."""
        app = ConfigApp(_simple_pages())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
        assert ConfigApp.RESULT is None

    @pytest.mark.asyncio
    async def test_nested_values_roundtrip(self):
        """Nested initial values survive accept."""
        initial = {
            "root": ConfigValues(
                values={"enabled": True},
                childs={
                    "child": ConfigValues(values={"level": 42}),
                },
            ),
        }
        app = ConfigApp(_nested_pages(), initial=initial)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        assert ConfigApp.RESULT is not None
        root = ConfigApp.RESULT["root"]
        assert root.values["enabled"] is True
        assert "child" in root.childs
        assert root.childs["child"].values["level"] == 42
