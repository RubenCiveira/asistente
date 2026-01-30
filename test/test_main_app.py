"""Tests for window.MainApp."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import TabbedContent

from app.config import AppConfig
from app.context.session import Session


class TestMainApp:
    @pytest.mark.asyncio
    async def test_app_starts_with_one_session(self, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        cfg = AppConfig(config_path=cfg_path)
        cfg.save()

        with patch("app.config.default_config_path", return_value=cfg_path):
            from window import MainApp
            app = MainApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                assert len(app.sessions) >= 1
                assert app.active_session is not None

    @pytest.mark.asyncio
    async def test_app_creates_new_session(self, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        cfg = AppConfig(config_path=cfg_path)
        cfg.save()

        with patch("app.config.default_config_path", return_value=cfg_path):
            from window import MainApp
            app = MainApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                initial_count = len(app.sessions)
                await pilot.press("ctrl+n")
                await pilot.pause()
                assert len(app.sessions) == initial_count + 1

    @pytest.mark.asyncio
    async def test_header_shows_defaults(self, tmp_path):
        cfg_path = tmp_path / "cfg.json"
        cfg = AppConfig(config_path=cfg_path)
        cfg.save()

        with patch("app.config.default_config_path", return_value=cfg_path):
            from window import MainApp
            app = MainApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                assert "Sin workspace" in app.title
