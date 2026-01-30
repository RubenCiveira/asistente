"""Tests for app.context.project.Project."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.context.project import Project


class TestProjectLoadOrCreate:
    def test_creates_new_project(self, tmp_path):
        prj = Project.load_or_create(tmp_path / "myproject")
        assert prj.name == "myproject"
        assert prj.status == "active"
        config = tmp_path / "myproject" / ".conf" / "assistants" / "project.json"
        assert config.exists()

    def test_reload_preserves_id(self, tmp_path):
        d = tmp_path / "proj"
        prj1 = Project.load_or_create(d)
        prj2 = Project.load_or_create(d)
        assert prj1.id == prj2.id

    def test_id_is_valid_uuid(self, tmp_path):
        prj = Project.load_or_create(tmp_path / "p")
        uuid.UUID(prj.id)

    def test_creates_directory_if_missing(self, tmp_path):
        d = tmp_path / "deep" / "nested" / "project"
        prj = Project.load_or_create(d)
        assert d.exists()
        assert prj.root_dir == d.resolve()

    def test_default_topics_empty(self, tmp_path):
        prj = Project.load_or_create(tmp_path / "proj")
        assert prj.topics == []


class TestProjectSave:
    def test_metadata_persists(self, tmp_path):
        d = tmp_path / "proj"
        prj = Project.load_or_create(d)
        prj.metadata["key"] = "value"
        prj.save()

        prj2 = Project.load_or_create(d)
        assert prj2.metadata["key"] == "value"

    def test_save_creates_config_directory(self, tmp_path):
        d = tmp_path / "proj"
        d.mkdir()
        prj = Project(
            id=str(uuid.uuid4()),
            name="test",
            description="",
            status="active",
            root_dir=d,
        )
        prj.save()
        config = d / ".conf" / "assistants" / "project.json"
        assert config.exists()
        data = json.loads(config.read_text())
        assert data["name"] == "test"


class TestProjectTopics:
    def test_topics_round_trip(self, tmp_path):
        d = tmp_path / "proj"
        prj = Project.load_or_create(d)
        prj.topics = ["docs", "code"]
        prj.save()
        prj2 = Project.load_or_create(d)
        assert prj2.topics == ["docs", "code"]

    def test_topics_pruned_on_load(self, tmp_path):
        d = tmp_path / "proj"
        d.mkdir(parents=True)
        config_path = d / ".conf" / "assistants" / "project.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps({
            "id": str(uuid.uuid4()),
            "name": "proj",
            "description": "",
            "status": "active",
            "metadata": {},
            "topics": ["valid", "stale", "also_valid"],
        }))
        prj = Project.load_or_create(d, valid_topics={"valid", "also_valid"})
        assert prj.topics == ["valid", "also_valid"]
        # Should have re-saved
        data = json.loads(config_path.read_text())
        assert data["topics"] == ["valid", "also_valid"]

    def test_topics_not_pruned_without_valid_topics(self, tmp_path):
        d = tmp_path / "proj"
        prj = Project.load_or_create(d)
        prj.topics = ["anything", "goes"]
        prj.save()
        prj2 = Project.load_or_create(d)
        assert prj2.topics == ["anything", "goes"]

    def test_topics_pruned_on_save(self, tmp_path):
        d = tmp_path / "proj"
        prj = Project.load_or_create(d)
        prj.topics = ["keep", "remove"]
        prj.save(valid_topics={"keep"})
        assert prj.topics == ["keep"]
        config_path = d / ".conf" / "assistants" / "project.json"
        data = json.loads(config_path.read_text())
        assert data["topics"] == ["keep"]
