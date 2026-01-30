"""Tests for app.context.session."""

from __future__ import annotations

import uuid

from app.context.session import Session


class TestSession:
    def test_default_id_is_uuid(self):
        s = Session()
        uuid.UUID(s.id)  # raises if invalid

    def test_unique_ids(self):
        ids = {Session().id for _ in range(100)}
        assert len(ids) == 100

    def test_explicit_id(self):
        s = Session(id="custom-id")
        assert s.id == "custom-id"

    def test_defaults_none(self):
        s = Session()
        assert s.workspace is None
        assert s.project is None
