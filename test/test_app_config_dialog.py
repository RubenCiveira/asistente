"""Tests for app.ui.textual.widgets.app_config_dialog."""

from __future__ import annotations

from typing import Dict, List

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from app.ui.textual.widgets.config_dialog import ConfigPage, ConfigValues
from app.ui.textual.widgets.config_provider import ConfigProvider
from app.ui.textual.widgets.app_config_dialog import AppConfigDialog


# ── Stub provider ────────────────────────────────────────────────────


class StubProvider(ConfigProvider):
    """Minimal provider that records save_config calls."""

    def __init__(self, page: ConfigPage, values: ConfigValues | None = None):
        self._page = page
        self._values = values or ConfigValues()
        self.saved: List[Dict[str, ConfigValues]] = []

    def config_page(self) -> ConfigPage:
        return self._page

    def config_values(self) -> ConfigValues:
        return self._values

    def save_config(self, values: Dict[str, ConfigValues]) -> None:
        self.saved.append(values)


# ── Helper apps ──────────────────────────────────────────────────────


class ProviderApp(App):
    """Push AppConfigDialog on mount via push_screen + callback."""

    RESULT = "_UNSET"

    def __init__(self, providers: List[ConfigProvider]):
        super().__init__()
        self._providers = providers
        ProviderApp.RESULT = "_UNSET"

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            AppConfigDialog(self._providers),
            callback=self._on_result,
        )

    def _on_result(self, result):
        ProviderApp.RESULT = result
        self.exit()


class ApplyProviderApp(App):
    """App that captures Applied messages from AppConfigDialog."""

    APPLIED_VALUES = None
    DISMISSED = False

    def __init__(self, providers: List[ConfigProvider]):
        super().__init__()
        self._providers = providers
        ApplyProviderApp.APPLIED_VALUES = None
        ApplyProviderApp.DISMISSED = False

    def compose(self) -> ComposeResult:
        yield Button("open", id="open")

    def on_mount(self) -> None:
        self.push_screen(
            AppConfigDialog(self._providers),
            callback=self._on_result,
        )

    def _on_result(self, result):
        ApplyProviderApp.DISMISSED = True
        self.exit()

    def on_config_dialog_applied(self, event: AppConfigDialog.Applied) -> None:
        ApplyProviderApp.APPLIED_VALUES = event.values


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_provider(page_id: str, field: str, value=None) -> StubProvider:
    page = ConfigPage(
        id=page_id,
        title=page_id.capitalize(),
        schema={
            "type": "object",
            "properties": {
                field: {"type": "string"},
            },
        },
    )
    values = ConfigValues(values={field: value}) if value is not None else ConfigValues()
    return StubProvider(page, values)


# ── Tests ────────────────────────────────────────────────────────────


class TestAppConfigDialog:
    @pytest.mark.asyncio
    async def test_accept_calls_save_config(self):
        """Accept triggers save_config on every provider."""
        p1 = _make_provider("general", "name", "test")
        p2 = _make_provider("display", "theme", "dark")
        app = ProviderApp([p1, p2])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        assert len(p1.saved) == 1
        assert len(p2.saved) == 1
        # Both receive the same full dict
        assert "general" in p1.saved[0]
        assert "display" in p1.saved[0]
        assert p1.saved[0] == p2.saved[0]

    @pytest.mark.asyncio
    async def test_apply_calls_save_config(self):
        """Apply triggers save_config without closing."""
        p = _make_provider("general", "name", "applied")
        app = ApplyProviderApp([p])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#apply")
            await pilot.pause()

            assert len(p.saved) == 1
            assert ApplyProviderApp.APPLIED_VALUES is not None
            assert ApplyProviderApp.DISMISSED is False

            await pilot.click("#cancel")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_cancel_does_not_call_save(self):
        """Cancel dismisses without calling save_config."""
        p = _make_provider("general", "name", "nope")
        app = ProviderApp([p])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()

        assert len(p.saved) == 0
        assert ProviderApp.RESULT is None

    @pytest.mark.asyncio
    async def test_initial_values_from_providers(self):
        """config_values() pre-populates form fields."""
        p = _make_provider("general", "name", "hello")
        app = ProviderApp([p])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        assert ProviderApp.RESULT is not None
        assert ProviderApp.RESULT["general"].values["name"] == "hello"

    @pytest.mark.asyncio
    async def test_multiple_providers(self):
        """Multiple providers each contribute a page."""
        p1 = _make_provider("alpha", "a_field", "a_val")
        p2 = _make_provider("beta", "b_field", "b_val")
        p3 = _make_provider("gamma", "g_field", "g_val")
        app = ProviderApp([p1, p2, p3])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.click("#accept")
            await pilot.pause()

        result = ProviderApp.RESULT
        assert result is not None
        assert "alpha" in result
        assert "beta" in result
        assert "gamma" in result
        assert result["alpha"].values["a_field"] == "a_val"
        assert result["beta"].values["b_field"] == "b_val"
        assert result["gamma"].values["g_field"] == "g_val"
        # Every provider was notified
        assert len(p1.saved) == 1
        assert len(p2.saved) == 1
        assert len(p3.saved) == 1
