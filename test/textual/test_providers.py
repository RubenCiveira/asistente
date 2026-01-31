"""Tests for completion providers."""

from app.ui.textual.completion_provider.slash_provider import SlashCommandProvider
from app.ui.textual.completion_provider.at_provider import ContextProvider
from app.ui.textual.completion_provider.colon_provider import PowerCommandProvider
from app.ui.textual.completion_provider.hash_provider import SemanticProvider


class TestSlashCommandProvider:
    def setup_method(self):
        self.provider = SlashCommandProvider()

    def test_empty_prefix_returns_all(self):
        items = self.provider("")
        assert len(items) == 5

    def test_matching_prefix(self):
        items = self.provider("work")
        assert len(items) == 1
        assert str(items[0].main) == "workspace"

    def test_no_match(self):
        items = self.provider("zzz")
        assert len(items) == 0

    def test_partial_prefix(self):
        items = self.provider("p")
        assert len(items) == 1
        assert str(items[0].main) == "project"

    def test_items_have_prefix_icon(self):
        items = self.provider("")
        for item in items:
            assert item.prefix is not None


class TestContextProvider:
    def setup_method(self):
        self.provider = ContextProvider()

    def test_empty_prefix_returns_all(self):
        items = self.provider("")
        assert len(items) >= 5

    def test_matching_prefix(self):
        items = self.provider("README")
        assert len(items) == 1
        assert str(items[0].main) == "README.md"

    def test_no_match(self):
        items = self.provider("zzz")
        assert len(items) == 0

    def test_src_prefix_expands(self):
        items = self.provider("src/")
        assert len(items) >= 1


class TestPowerCommandProvider:
    def setup_method(self):
        self.provider = PowerCommandProvider()

    def test_empty_prefix_returns_all(self):
        items = self.provider("")
        assert len(items) == 5

    def test_matching_prefix(self):
        items = self.provider("cl")
        assert len(items) == 1
        assert str(items[0].main) == "clear"

    def test_no_match(self):
        items = self.provider("zzz")
        assert len(items) == 0


class TestSemanticProvider:
    def setup_method(self):
        self.provider = SemanticProvider()

    def test_empty_prefix_returns_all(self):
        items = self.provider("")
        assert len(items) == 5

    def test_case_insensitive(self):
        items = self.provider("user")
        assert len(items) == 1
        assert str(items[0].main) == "User"

    def test_upper_case_prefix(self):
        items = self.provider("Work")
        assert len(items) == 1
        assert str(items[0].main) == "Workspace"

    def test_no_match(self):
        items = self.provider("zzz")
        assert len(items) == 0
