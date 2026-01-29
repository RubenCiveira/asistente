from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List

from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button
from textual.containers import Vertical, Horizontal

from textual_autocomplete import AutoComplete, DropdownItem
from textual_autocomplete._autocomplete import TargetState  # callback state (v4)

class PathDialog(ModalScreen[Optional[Path]]):
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
        mode: str = "read",              # "read" | "write"
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
        self.mode = mode
        self.select = select
        self.initial_path = initial_path
        self.name_filter = re.compile(name_filter) if name_filter else None
        self.relative_check_path = relative_check_path
        self.title = title
        self.sub_title = sub_title
        self.max_suggestions = max_suggestions

    def compose(self):
        initial = str(self.initial_path) if self.initial_path else ""

        input_widget = Input(
            placeholder=str(self.root_dir),
            value=initial,
            id="path_input",
        )

        yield Vertical(
            Static(self.title, id="title"),
            Static(f"[i]{self.sub_title}[/i]", id="subtitle"),
            input_widget,
            Static(f"[i]Root: {self.root_dir}[/i]", id="root_label"),
            # AutoComplete se monta aparte y apunta al Input como target (v4)
            AutoComplete(target=input_widget, candidates=self._candidates, id="ac"),
            Static("", id="error"),
            Horizontal(
                Button("Cancel", id="btn_cancel"),
                Button("OK", variant="primary", id="btn_ok"),
                id="buttons",
            ),
            id="dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#path_input", Input).focus()

    # ---------- Actions / Buttons ----------

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
        elif event.button.id == "btn_ok":
            self._try_accept()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path_input":
            self._try_accept()

    # ---------- AutoComplete callback (v4) ----------

    def _candidates(self, state):
        text = state.text or ""

        try:
            # "/" significa listar root
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

            items = []

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

                # if self.select == "file" and p.is_dir():
                #     continue
                if self.select == "dir" and p.is_file():
                    continue

                # 🔑 mostrar RELATIVO
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
            return []


    # ---------- Validation / Accept ----------

    def _try_accept(self) -> None:
        raw = self.query_one("#path_input", Input).value
        path = self._validate(raw)
        if path is not None:
            self.dismiss(path)

    def _validate(self, raw: str) -> Optional[Path]:
        self._show_error("")

        absolute = self._to_absolute(raw)

        if not absolute.is_relative_to(self.root_dir):
            self._show_error("Path outside root")
            return None

        if self.mode == "read" and not absolute.exists():
            self._show_error("Path does not exist")
            return None

        if self.select == "file" and absolute.exists() and not absolute.is_file():
            self._show_error("File required")
            return None

        if self.select == "dir" and absolute.exists() and not absolute.is_dir():
            self._show_error("Directory required")
            return None

        if self.mode == "write" and absolute.exists():
            self._show_error("Path exists (confirm overwrite)")
            return None

        if self.relative_check_path:
            check = absolute / self.relative_check_path
            if check.exists():
                self._show_error(f"'{self.relative_check_path}' already exists")
                return None

        return absolute


    def _show_error(self, msg: str) -> None:
        self.query_one("#error", Static).update(f"[red]{msg}[/red]" if msg else "")

    def _to_absolute(self, relative: str) -> Path:
        rel = relative.lstrip("/")  # "/" → ""
        return (self.root_dir / rel).resolve(strict=False)
