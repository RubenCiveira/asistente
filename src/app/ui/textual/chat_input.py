from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from textual.widget import Widget
from textual.widgets import Input
from textual.reactive import reactive
from textual.events import Key
from textual.message import Message

from textual_autocomplete import AutoComplete, DropdownItem
from textual_autocomplete._autocomplete import TargetState
from app.ui.textual.token_aware_auto_complete import TokenAwareAutoComplete


# Tipo del provider de autocompletado
CompletionProvider = Callable[[str], List[DropdownItem]]

class ChatInput(Widget):
    """
    Chat input with trigger-based autocomplete (/, @, :, #, ...)
    """

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
    }

    #chat_input {
        border: round $accent;
        padding: 0 1;
    }
    
    AutoComplete {
        margin-top: -6;
    }
    """

    value: reactive[str] = reactive("")

    def __init__(
        self,
        *,
        triggers: Dict[str, CompletionProvider],
        placeholder: str = "Escribe aquí…",
        id: Optional[str] = None,
    ):
        super().__init__(id=id)
        self.triggers = triggers
        self.placeholder = placeholder

    # ─────────────────────────────────────
    # UI
    # ─────────────────────────────────────

    def compose(self):
        self._input = Input(
            placeholder=self.placeholder,
            id="chat_input",
        )

        yield self._input
        yield TokenAwareAutoComplete(
            target=self._input,
            candidates=self._candidates,
            resolvers=self.triggers,
        )

    def on_mount(self) -> None:
        self._input.focus()

    # ─────────────────────────────────────
    # Autocomplete core
    # ─────────────────────────────────────

    def _candidates(self, state: TargetState) -> List[DropdownItem]:
        text = state.text or ""
        cursor = state.cursor_position
        before = text[:cursor]

        trigger_pos = -1
        trigger_char = None

        for t in self.triggers.keys():
            pos = before.rfind(t)
            if pos > trigger_pos:
                trigger_pos = pos
                trigger_char = t

        if trigger_pos == -1 or trigger_char is None:
            return []

        config = self.triggers[trigger_char]
        prefix = before[trigger_pos + 1 :]

        raw_items = config(prefix)
        items: List[DropdownItem] = []

        for item in raw_items:
            items.append(
                DropdownItem(
                    main=item.main + " ",
                    prefix=item.prefix,
                )
            )

        # marcar para mover cursor al final tras insertar
        return items

    # ─────────────────────────────────────
    # Submit / Events
    # ─────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is not self._input:
            return
        text = (event.value or "")
        if not text:
            return

        self.value = text
        self.post_message(self.Submitted(text))
        self._input.value = ""

    # Mensaje propio del componente
    class Submitted(Message):
        def __init__(self, value: str):
            super().__init__()
            self.value = value