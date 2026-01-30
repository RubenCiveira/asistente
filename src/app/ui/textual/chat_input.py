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
    """

    value: reactive[str] = reactive("")
    CONTINUE_WRITE_VALID_CHARS = ("/", ":", "#", "@", ".")

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
        self._autocomplete = TokenAwareAutoComplete(
            target=self._input,
            candidates=self._candidates,
            resolvers=self.triggers,
        )

        yield self._input
        yield self._autocomplete

    def on_mount(self) -> None:
        self._input.focus()

    # ─────────────────────────────────────
    # Autocomplete core
    # ─────────────────────────────────────

    def _candidates(self, state: TargetState) -> List[DropdownItem]:
        text = state.text or ""
        cursor = state.cursor_position
        before = text[:cursor]

        trigger_pos, trigger_len, trigger_char = (
            self._autocomplete._find_last_trigger(before)
        )

        if trigger_pos == -1 or trigger_char is None:
            return []

        provider = self.triggers[trigger_char]

        # token entre trigger y cursor
        prefix = before[trigger_pos + trigger_len :]

        # si hay espacios, no autocomplete
        if any(ch.isspace() for ch in prefix):
            return []

        raw_items = provider(prefix)

        return [
            DropdownItem(
                main=item.main + ("" if str(item.main).endswith( self.CONTINUE_WRITE_VALID_CHARS ) else " "),
                prefix=item.prefix,
            )
            for item in raw_items
        ]

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