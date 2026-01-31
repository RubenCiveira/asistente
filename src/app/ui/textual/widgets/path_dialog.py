"""File and directory browser modal with autocomplete suggestions.

Presents an input field where the user can type a path relative to a given
root directory.  Suggestions are provided via ``textual-autocomplete`` and
the result is validated against configurable constraints (must exist, file
vs. directory, name filter, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List

from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button
from textual.containers import Vertical, Horizontal

from .path_field import PathField


class PathDialog(ModalScreen[Optional[Path]]):
    """Modal path-selection dialog with filesystem autocomplete.

    The dialog shows an input field pre-populated with an optional
    *initial_path* and offers autocomplete suggestions drawn from the
    filesystem under *root_dir*.  On submission the entered value is
    validated and the resolved :class:`~pathlib.Path` is returned, or
    ``None`` when the user cancels.

    Args:
        root_dir: Base directory; all paths are resolved relative to it.
        must_exist: When ``True`` the selected path must already exist.
        warn_if_exists: When ``True`` an existing path is rejected.
        select: Constrain selection to ``"file"``, ``"dir"`` or ``"any"``.
        initial_path: Pre-fill the input with this path.
        name_filter: Optional regex applied to entry names.
        relative_check_path: If set, reject paths where this relative
            sub-path already exists.
        title: Dialog heading.
        sub_title: Secondary text shown below the title.
        max_suggestions: Maximum number of autocomplete suggestions.
    """

    DEFAULT_CSS = """
    PathDialog {
        align: center middle;
        background: $surface 80%;
    }

    #dialog {
        width: 80%;
        max-width: 110;
        min-width: 60;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #title { text-style: bold; margin-bottom: 1; }
    #error { height: auto; margin-top: 1; }
    #buttons { margin-top: 1; align: right middle; height: auto; }

    #ac {
        layer: overlay;
    }
    #ac > * {
        background: $panel;
        border: round $primary;
        padding: 0 1;
    }
    #ac OptionList {
        background: $panel;
        border: round $primary;
        padding: 0 1;
    }
    #ac OptionList > .option-list--option {
        padding: 0 1;
    }
    #ac OptionList > .option-list--option.-highlighted {
        background: $primary 20%;
        text-style: bold;
    }
    #ac ListView {
        background: $panel;
        border: round $primary;
        padding: 0 1;
    }
    #ac ListItem.--highlight {
        background: $primary 20%;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        *,
        root_dir: Path,
        must_exist: bool = True,
        warn_if_exists: bool = False,
        select: str = "any",             # "file" | "dir" | "any"
        initial_path: Path | None = None,
        name_filter: str | None = None,  # regex sobre el nombre (p.name)
        relative_check_path: Path | None = None,
        title: str = "Select path",
        sub_title: str = "",
        max_suggestions: int = 30,
    ):
        super().__init__()
        self.root_dir = root_dir.expanduser().resolve()
        self.must_exist = must_exist
        self.warn_if_exists = warn_if_exists
        self.select = select
        self.initial_path = initial_path
        self.name_filter = re.compile(name_filter) if name_filter else None
        self.relative_check_path = relative_check_path
        self.title = title
        self.sub_title = sub_title
        self.max_suggestions = max_suggestions
        self._path_field: PathField | None = None

    def compose(self):
        """Build the dialog widget tree with input, autocomplete and buttons."""
        self._path_field = PathField(
            root_dir=self.root_dir,
            must_exist=self.must_exist,
            warn_if_exists=self.warn_if_exists,
            select=self.select,
            initial_path=self.initial_path,
            name_filter=self.name_filter.pattern if self.name_filter else None,
            relative_check_path=self.relative_check_path,
            max_suggestions=self.max_suggestions,
            placeholder=str(self.root_dir),
            input_id="path_input",
            autocomplete_id="ac",
        )

        yield Vertical(
            Static(str(self.title or ""), id="title"),
            Static(f"[i]{self.sub_title or ''}[/i]", id="subtitle"),
            self._path_field,
            Static(f"[i]Root: {self.root_dir}[/i]", id="root_label"),
            Static("", id="error"),
            Horizontal(
                Button("Cancel", id="btn_cancel"),
                Button("OK", variant="primary", id="btn_ok"),
                id="buttons",
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        """Focus the path input on mount."""
        if self._path_field is not None:
            self._path_field.focus_input()

    # ---------- Actions / Buttons ----------

    def action_cancel(self) -> None:
        """Handle Escape by dismissing with ``None``."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses to cancel or accept."""
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_ok":
            self._try_accept()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Treat Enter in the path input as an accept attempt."""
        if event.input.id == "path_input":
            self._try_accept()

    # ---------- Validation / Accept ----------

    def _try_accept(self) -> None:
        """Read the input value, validate it and dismiss if valid."""
        if self._path_field is None:
            return
        raw = self._path_field.get_value()
        path = self._validate(raw)
        if path is not None:
            self.dismiss(path)

    def _validate(self, raw: str) -> Optional[Path]:
        """Validate the raw input string against all configured constraints.

        Args:
            raw: Text entered by the user (relative to *root_dir*).

        Returns:
            The resolved absolute path on success, or ``None`` when
            validation fails (an error message is shown in the dialog).
        """
        self._show_error("")

        absolute = self._to_absolute(raw)

        if not absolute.is_relative_to(self.root_dir):
            self._show_error("Path outside root")
            return None

        if self.must_exist and not absolute.exists():
            self._show_error("Path does not exist")
            return None

        if self.select == "file" and absolute.exists() and not absolute.is_file():
            self._show_error("File required")
            return None

        if self.select == "dir" and absolute.exists() and not absolute.is_dir():
            self._show_error("Directory required")
            return None

        if self.warn_if_exists and absolute.exists():
            self._show_error("Path already exists")
            return None

        if self.relative_check_path:
            check = absolute / self.relative_check_path
            if check.exists():
                self._show_error(f"'{self.relative_check_path}' already exists")
                return None

        return absolute


    def _show_error(self, msg: str) -> None:
        """Display *msg* in the error label (red), or clear it when empty."""
        self.query_one("#error", Static).update(f"[red]{msg}[/red]" if msg else "")

    def _to_absolute(self, relative: str) -> Path:
        """Convert a user-entered relative string to an absolute path.

        Leading ``/`` characters are stripped so that ``/sub`` resolves to
        ``root_dir / sub``.
        """
        rel = relative.lstrip("/")  # "/" → ""
        return (self.root_dir / rel).resolve(strict=False)
