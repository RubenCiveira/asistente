"""Tests for app.config.AppConfig."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import AppConfig


class TestAppConfigLoad:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = AppConfig.load(tmp_path / "missing.json")
        assert cfg.active_workspace is None
        assert cfg.recent_workspaces == []
        assert cfg.sessions == []
        assert cfg.active_session_index == 0

    def test_load_existing_file(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({
            "active_workspace": "/ws",
            "recent_workspaces": ["/ws", "/ws2"],
            "sessions": [{"id": "s1", "workspace": "/ws", "project": None}],
            "active_session_index": 0,
        }))
        cfg = AppConfig.load(f)
        assert cfg.active_workspace == Path("/ws")
        assert len(cfg.recent_workspaces) == 2
        assert cfg.sessions[0]["id"] == "s1"


class TestAppConfigSave:
    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "cfg.json"
        cfg = AppConfig(config_path=nested, active_workspace=Path("/ws"))
        cfg.save()
        assert nested.exists()
        data = json.loads(nested.read_text())
        assert data["active_workspace"] == "/ws"

    def test_round_trip(self, tmp_path):
        f = tmp_path / "cfg.json"
        cfg = AppConfig(config_path=f, active_workspace=Path("/w"))
        cfg.recent_workspaces = [Path("/w")]
        cfg.sessions = [{"id": "x"}]
        cfg.active_session_index = 0
        cfg.save()
        loaded = AppConfig.load(f)
        assert loaded.active_workspace == Path("/w")
        assert loaded.recent_workspaces == [Path("/w")]
        assert loaded.sessions == [{"id": "x"}]


class TestSetActiveWorkspace:
    def test_sets_active_and_prepends_to_recent(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        ws = tmp_path / "ws1"
        ws.mkdir()
        cfg.set_active_workspace(ws)
        assert cfg.active_workspace == ws.resolve()
        assert cfg.recent_workspaces[0] == ws.resolve()

    def test_deduplicates(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        ws = tmp_path / "ws1"
        ws.mkdir()
        cfg.set_active_workspace(ws)
        cfg.set_active_workspace(ws)
        assert cfg.recent_workspaces.count(ws.resolve()) == 1

    def test_limits_to_10(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        for i in range(15):
            d = tmp_path / f"ws{i}"
            d.mkdir()
            cfg.set_active_workspace(d)
        assert len(cfg.recent_workspaces) == 10
        # Most recent should be first
        assert cfg.recent_workspaces[0] == (tmp_path / "ws14").resolve()
