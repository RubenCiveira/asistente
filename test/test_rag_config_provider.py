"""Tests for app.ui.textual.rag_config_provider."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.config import AppConfig, PostgresRagConfig, Topic
from app.context.workspace import Workspace
from app.context.project import Project
from app.ui.textual.widgets.config_dialog import ConfigValues
from app.ui.textual.config_provider.rag_config_provider import RagConfigProvider, _topic_selection_schema


# ── Stub window ──────────────────────────────────────────────────────


class StubWindow:
    """Minimal stand-in for MainApp, providing config + active context."""

    def __init__(self, config: AppConfig, workspace=None, project=None):
        self.config = config
        self._workspace = workspace
        self._project = project

    def get_active_workspace(self):
        return self._workspace

    def get_active_project(self):
        return self._project


# ── config_page tests ────────────────────────────────────────────────


class TestConfigPage:
    def test_structure(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        page = provider.config_page()

        assert page.id == "rag"
        assert page.title == "RAG"
        assert len(page.children) == 1

        topics_page = page.children[0]
        assert topics_page.id == "topics"
        assert len(topics_page.children) == 2
        assert topics_page.children[0].id == "workspace_topics"
        assert topics_page.children[1].id == "project_topics"

    def test_schema_fields(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        page = provider.config_page()

        props = page.schema["properties"]
        assert "host" in props
        assert "port" in props
        assert "database" in props
        assert "user" in props
        assert "password" in props
        assert "table" in props
        assert props["port"]["type"] == "integer"

    def test_topic_options_populated(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        cfg.topics = [Topic(name="docs", path="/docs"), Topic(name="code", path="/code")]
        provider = RagConfigProvider(StubWindow(cfg))
        page = provider.config_page()

        ws_schema = page.children[0].children[0].schema
        items = ws_schema["properties"]["topics"]["items"]
        assert "oneOf" in items
        names = [opt["const"] for opt in items["oneOf"]]
        assert names == ["docs", "code"]

    def test_topic_options_empty(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        page = provider.config_page()

        ws_schema = page.children[0].children[0].schema
        items = ws_schema["properties"]["topics"]["items"]
        assert items == {"type": "string"}


# ── config_values tests ──────────────────────────────────────────────


class TestConfigValues:
    def test_reads_postgres(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        cfg.postgres_rag = PostgresRagConfig(
            host="db.test", port=5433, database="mydb",
            user="admin", password="secret", table="emb",
        )
        provider = RagConfigProvider(StubWindow(cfg))
        cv = provider.config_values()

        assert cv.values["host"] == "db.test"
        assert cv.values["port"] == 5433
        assert cv.values["database"] == "mydb"
        assert cv.values["user"] == "admin"
        assert cv.values["password"] == "secret"
        assert cv.values["table"] == "emb"

    def test_reads_topics(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        cfg.topics = [
            Topic(name="docs", path="/data/docs"),
            Topic(name="code", path="/src"),
        ]
        provider = RagConfigProvider(StubWindow(cfg))
        cv = provider.config_values()

        entries = cv.childs["topics"].values["entries"]
        assert entries == ["docs:/data/docs", "code:/src"]

    def test_reads_workspace_topics(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        ws = Workspace.load_or_create(tmp_path / "ws")
        ws.topics = ["docs", "code"]
        provider = RagConfigProvider(StubWindow(cfg, workspace=ws))
        cv = provider.config_values()

        ws_topics = cv.childs["topics"].childs["workspace_topics"].values["topics"]
        assert ws_topics == ["docs", "code"]

    def test_reads_project_topics(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        prj = Project.load_or_create(tmp_path / "prj")
        prj.topics = ["docs"]
        provider = RagConfigProvider(StubWindow(cfg, project=prj))
        cv = provider.config_values()

        prj_topics = cv.childs["topics"].childs["project_topics"].values["topics"]
        assert prj_topics == ["docs"]

    def test_no_workspace(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        cv = provider.config_values()

        ws_topics = cv.childs["topics"].childs["workspace_topics"].values["topics"]
        assert ws_topics == []

    def test_no_project(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        cv = provider.config_values()

        prj_topics = cv.childs["topics"].childs["project_topics"].values["topics"]
        assert prj_topics == []


# ── save_config tests ────────────────────────────────────────────────


class TestSaveConfig:
    def _make_values(
        self,
        host="localhost", port=5432, database="", user="", password="", table="",
        entries=None, ws_topics=None, prj_topics=None,
    ):
        return {
            "rag": ConfigValues(
                values={
                    "host": host,
                    "port": port,
                    "database": database,
                    "user": user,
                    "password": password,
                    "table": table,
                },
                childs={
                    "topics": ConfigValues(
                        values={"entries": entries or []},
                        childs={
                            "workspace_topics": ConfigValues(
                                values={"topics": ws_topics or []},
                            ),
                            "project_topics": ConfigValues(
                                values={"topics": prj_topics or []},
                            ),
                        },
                    ),
                },
            ),
        }

    def test_updates_postgres(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(
            host="db.prod", port=5433, database="prod",
            user="admin", password="s3cret", table="vectors",
        )
        provider.save_config(values)

        assert cfg.postgres_rag.host == "db.prod"
        assert cfg.postgres_rag.port == 5433
        assert cfg.postgres_rag.database == "prod"
        assert cfg.postgres_rag.user == "admin"
        assert cfg.postgres_rag.password == "s3cret"
        assert cfg.postgres_rag.table == "vectors"
        # Persisted to disk
        assert (tmp_path / "c.json").exists()

    def test_parses_topic_entries(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(entries=["docs:/data/docs", "code:/src/code"])
        provider.save_config(values)

        assert len(cfg.topics) == 2
        assert cfg.topics[0].name == "docs"
        assert cfg.topics[0].path == "/data/docs"
        assert cfg.topics[0].type == "directory"
        assert cfg.topics[1].name == "code"
        assert cfg.topics[1].path == "/src/code"

    def test_parses_entry_without_path(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(entries=["orphan"])
        provider.save_config(values)

        assert len(cfg.topics) == 1
        assert cfg.topics[0].name == "orphan"
        assert cfg.topics[0].path == ""

    def test_skips_empty_entries(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(entries=["good:/path", ":/bad", ""])
        provider.save_config(values)

        assert len(cfg.topics) == 1
        assert cfg.topics[0].name == "good"

    def test_updates_workspace_topics(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        ws = Workspace.load_or_create(tmp_path / "ws")
        provider = RagConfigProvider(StubWindow(cfg, workspace=ws))

        values = self._make_values(
            entries=["docs:/docs", "code:/code"],
            ws_topics=["docs", "code", "stale"],
        )
        provider.save_config(values)

        # "stale" should be pruned since it's not in the new topic definitions
        assert "stale" not in ws.topics
        assert "docs" in ws.topics
        assert "code" in ws.topics

    def test_updates_project_topics(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        prj = Project.load_or_create(tmp_path / "prj")
        provider = RagConfigProvider(StubWindow(cfg, project=prj))

        values = self._make_values(
            entries=["docs:/docs"],
            prj_topics=["docs", "removed"],
        )
        provider.save_config(values)

        assert prj.topics == ["docs"]

    def test_no_workspace_no_error(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(ws_topics=["anything"])
        provider.save_config(values)
        # Should not raise

    def test_no_project_no_error(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))

        values = self._make_values(prj_topics=["anything"])
        provider.save_config(values)
        # Should not raise

    def test_no_rag_key_is_noop(self, tmp_path):
        cfg = AppConfig(config_path=tmp_path / "c.json")
        provider = RagConfigProvider(StubWindow(cfg))
        provider.save_config({})
        # Nothing saved — config file should not exist
        assert not (tmp_path / "c.json").exists()


# ── helper function tests ────────────────────────────────────────────


class TestTopicSelectionSchema:
    def test_with_options(self):
        options = [{"const": "a", "title": "A"}, {"const": "b", "title": "B"}]
        schema = _topic_selection_schema(options, "desc")
        items = schema["properties"]["topics"]["items"]
        assert items["oneOf"] == options

    def test_empty_options(self):
        schema = _topic_selection_schema([], "desc")
        items = schema["properties"]["topics"]["items"]
        assert items == {"type": "string"}
