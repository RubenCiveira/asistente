"""Tests for app.context.keywords.Keywords."""

from app.context.keywords import Keywords


class TestMustContinue:
    def setup_method(self):
        self.kw = Keywords(["/", "@", ":", "#"])

    def test_slash_continues(self):
        assert self.kw.must_continue("src/") is True

    def test_colon_continues(self):
        assert self.kw.must_continue("agent:") is True

    def test_hash_continues(self):
        assert self.kw.must_continue("tag#") is True

    def test_at_continues(self):
        assert self.kw.must_continue("user@") is True

    def test_dot_continues(self):
        assert self.kw.must_continue("file.") is True

    def test_regular_text_does_not_continue(self):
        assert self.kw.must_continue("hello") is False

    def test_space_does_not_continue(self):
        assert self.kw.must_continue("hello ") is False

    def test_empty_does_not_continue(self):
        assert self.kw.must_continue("") is False


class TestFindLastTrigger:
    def setup_method(self):
        self.kw = Keywords(["/", "@", ":", "#"])

    def test_no_trigger(self):
        pos, length, trigger = self.kw.find_last_trigger("hello world")
        assert pos == -1
        assert trigger is None

    def test_trigger_at_start(self):
        pos, length, trigger = self.kw.find_last_trigger("/workspace")
        assert pos == 0
        assert length == 1
        assert trigger == "/"

    def test_trigger_after_space(self):
        pos, length, trigger = self.kw.find_last_trigger("hello /ws")
        assert pos == 6
        assert trigger == "/"

    def test_trigger_after_tab(self):
        pos, length, trigger = self.kw.find_last_trigger("text\t@file")
        assert pos == 5
        assert trigger == "@"

    def test_trigger_after_paren(self):
        pos, length, trigger = self.kw.find_last_trigger("fn(#User")
        assert pos == 3
        assert trigger == "#"

    def test_trigger_not_valid_in_middle_of_word(self):
        pos, length, trigger = self.kw.find_last_trigger("hello@world")
        assert pos == -1
        assert trigger is None

    def test_rightmost_trigger_wins(self):
        pos, length, trigger = self.kw.find_last_trigger("/cmd @file")
        assert pos == 5
        assert trigger == "@"

    def test_empty_string(self):
        pos, length, trigger = self.kw.find_last_trigger("")
        assert pos == -1
        assert trigger is None

    def test_multi_char_trigger(self):
        kw = Keywords(["//", "/"])
        pos, length, trigger = kw.find_last_trigger("text //cmd")
        assert pos == 5
        assert length == 2
        assert trigger == "//"


class TestKeywordsInit:
    def test_stores_triggers(self):
        kw = Keywords(["/", "@"])
        # We can't directly inspect _triggers, but we can test find works
        pos, _, trigger = kw.find_last_trigger("/test")
        assert trigger == "/"
