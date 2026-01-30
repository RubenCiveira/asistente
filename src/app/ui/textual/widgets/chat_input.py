"""Chat input widget with trigger-based autocomplete.

Wraps a Textual :class:`~textual.widgets.Input` with a
:class:`~app.ui.textual.widgets.token_aware_auto_complete.TokenAwareAutoComplete`
overlay.  Each trigger character (``/``, ``@``, ``:``, ``#``, etc.) is
mapped to a :data:`CompletionProvider` callable that returns matching
:class:`~textual_autocomplete.DropdownItem` suggestions.
"""

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
from app.ui.textual.widgets.token_aware_auto_complete import TokenAwareAutoComplete

from app.context.keywords import Keywords

CompletionProvider = Callable[[str], List[DropdownItem]]
"""Type alias for a completion provider: receives a prefix and returns items."""


class ChatInput(Widget):
    """Composite widget providing a text input with trigger-based autocomplete.

    When the user types a trigger character (after whitespace or at the start
    of the line), the corresponding :data:`CompletionProvider` is invoked and
    matching suggestions appear in a dropdown.

    Args:
        keywords: :class:`~app.context.keywords.Keywords` instance managing
            trigger detection.
        triggers: Mapping from trigger strings to their completion providers.
        placeholder: Placeholder text shown when the input is empty.
        id: Optional widget identifier.
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
    # CONTINUE_WRITE_VALID_CHARS = ("/", ":", "#", "@", ".")

    def __init__(
        self,
        *,
        keywords: Keywords,
        triggers: Dict[str, CompletionProvider],
        placeholder: str = "Escribe aquí…",
        id: Optional[str] = None,
    ):
        """Initialise the chat input widget.

        Args:
            keywords: Keywords helper for trigger detection.
            triggers: Mapping of trigger string to provider callable.
            placeholder: Placeholder text for the inner Input.
            id: Optional widget DOM id.
        """
        super().__init__(id=id)
        self.triggers = triggers
        self.keywords = keywords
        self.placeholder = placeholder

    # ─────────────────────────────────────
    # UI
    # ─────────────────────────────────────

    def compose(self):
        """Build the widget tree: an Input and a TokenAwareAutoComplete overlay."""
        self._input = Input(
            placeholder=self.placeholder,
            id="chat_input",
        )
        self._autocomplete = TokenAwareAutoComplete(
            keywords=self.keywords,
            target=self._input,
            candidates=self._candidates,
            resolvers=self.triggers,
        )

        yield self._input
        yield self._autocomplete

    def on_mount(self) -> None:
        """Focus the inner input on mount."""
        self._input.focus()

    # ─────────────────────────────────────
    # Autocomplete core
    # ─────────────────────────────────────

    def _candidates(self, state: TargetState) -> List[DropdownItem]:
        """Return autocomplete suggestions for the current input state.

        Locates the last trigger in the text before the cursor, invokes the
        corresponding provider with the token typed after the trigger, and
        returns the filtered items.

        Args:
            state: Autocomplete target state with text and cursor position.

        Returns:
            A list of :class:`DropdownItem` suggestions.
        """
        text = state.text or ""
        cursor = state.cursor_position
        before = text[:cursor]

        trigger_pos, trigger_len, trigger_char = (
            # self._autocomplete._find_last_trigger(before)
            self.keywords.find_last_trigger(before)
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
                # main=item.main + ("" if str(item.main).endswith( self.CONTINUE_WRITE_VALID_CHARS ) else " "),
                main=item.main + ("" if self.keywords.must_continue(item.main) else " "),
                prefix=item.prefix,
            )
            for item in raw_items
        ]

    # ─────────────────────────────────────
    # Submit / Events
    # ─────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter: post a :class:`Submitted` message and clear the input."""
        if event.input is not self._input:
            return
        text = (event.value or "")
        if not text:
            return

        self.value = text
        self.post_message(self.Submitted(text))
        self._input.value = ""

    class Submitted(Message):
        """Message posted when the user submits text via Enter.

        Attributes:
            value: The submitted text.
        """

        def __init__(self, value: str):
            super().__init__()
            self.value = value