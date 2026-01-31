"""Reusable path input with filesystem autocomplete."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input

from textual_autocomplete import AutoComplete, DropdownItem
from textual_autocomplete._autocomplete import TargetState


class PathField(Vertical):
    """Input field with filesystem autocomplete suggestions."""

    def __init__(
        self,
        *,
        root_dir: Path,
        must_exist: bool = True,
        warn_if_exists: bool = False,
        select: str = "any",
        initial_path: Path | None = None,
        name_filter: str | None = None,
        relative_check_path: Path | None = None,
        max_suggestions: int = 30,
        placeholder: str | None = None,
        input_id: str = "path_input",
        autocomplete_id: str = "ac",
    ) -> None:
        super().__init__()
        self.root_dir = root_dir.expanduser().resolve()
        self.must_exist = must_exist
        self.warn_if_exists = warn_if_exists
        self.select = select
        self.initial_path = initial_path
        self.name_filter = re.compile(name_filter) if name_filter else None
        self.relative_check_path = relative_check_path
        self.max_suggestions = max_suggestions
        self._placeholder = placeholder or str(self.root_dir)
        self._input_id = input_id
        self._autocomplete_id = autocomplete_id
        self._input: Optional[Input] = None

    def compose(self) -> ComposeResult:
        initial = self._initial_value()
        self._input = Input(
            placeholder=self._placeholder,
            value=initial,
            id=self._input_id,
        )
        yield self._input
        yield AutoComplete(
            target=self._input,
            candidates=self._candidates,
            id=self._autocomplete_id,
        )

    def focus_input(self) -> None:
        if self._input is not None:
            self._input.focus()

    def get_value(self) -> str:
        if self._input is None:
            return ""
        return self._input.value

    def _initial_value(self) -> str:
        if not self.initial_path:
            return ""
        try:
            resolved = self.initial_path.expanduser().resolve()
            rel = resolved.relative_to(self.root_dir)
        except Exception:
            return ""
        return "/" + str(rel)

    def _candidates(self, state: TargetState) -> List[DropdownItem]:
        text = state.text or ""

        try:
            # "/" means list root
            rel = text.lstrip("/")
            base = (self.root_dir / rel).resolve(strict=False)
            if not base.is_relative_to(self.root_dir):
                return []
            ends_with_slash = text.endswith("/")
            if rel == ".":
                parent = self.root_dir
                prefix = "."
            elif rel == "/":
                parent = self.root_dir
                prefix = ""
            elif ends_with_slash:
                parent = base
                prefix = ""
            else:
                parent = base.parent
                prefix = base.name

            if not parent.exists() or not parent.is_dir():
                return []

            items: List[DropdownItem] = []

            entries = sorted(
                parent.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower())
            )
            for p in entries:
                p_abs = p.resolve(strict=False)
                if not (p_abs == self.root_dir or p_abs.is_relative_to(self.root_dir)):
                    continue
                if self.name_filter and not self.name_filter.match(p.name):
                    continue
                if rel != "." and p.name.startswith("."):
                    continue

                if prefix and not p.name.startswith(prefix):
                    continue

                if self.select == "dir" and p.is_file():
                    continue

                rel_path = p.relative_to(self.root_dir)

                items.append(
                    DropdownItem(
                        main="/" + str(rel_path),
                        prefix="📁 " if p.is_dir() else "📄 ",
                    )
                )

                if len(items) >= self.max_suggestions:
                    break
            return items

        except Exception:
            raise
