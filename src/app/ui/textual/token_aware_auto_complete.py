from __future__ import annotations

from typing import Mapping, Any, Iterable

from textual_autocomplete import AutoComplete
from textual_autocomplete.fuzzy_search import FuzzySearch
from textual_autocomplete._autocomplete import TargetState

class TokenFuzzySearch(FuzzySearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def match(self, query: str, candidate: str) -> tuple[float, Sequence[int]]:
        return super().match(candidate, candidate)

class TokenAwareAutoComplete(AutoComplete):
    """AutoComplete que filtra usando solo el token activo (tras el último trigger)."""

    def __init__(self, *args, resolvers: Mapping[str, Any], **kwargs):
        """
        resolvers: mapa donde las keys son los triggers ("/", "@", ":", "#", ...)
                   y el value puede ser lo que quieras (providers, TriggerConfig, etc.)
        """
        super().__init__(*args, **kwargs)
        self._fuzzy_search = TokenFuzzySearch()
        self._resolvers = resolvers
        self._triggers: list[str] = sorted(resolvers.keys(), key=len, reverse=True)

    # ── inserción: reemplazar solo el bloque activo
    def apply_completion(self, item: DropdownItem, state: TargetState) -> None:
        input_widget = self.target  # el Input target
        text = state.text or ""
        cursor = state.cursor_position
        before = text[:cursor]
        after = text[cursor:]

        trigger_pos, trigger_len = self._find_last_trigger(before)
        if trigger_pos == -1:
            return

        trigger = before[trigger_pos : trigger_pos + trigger_len]

        # texto entre trigger y cursor
        token = before[trigger_pos + trigger_len :]
        if any(ch.isspace() for ch in token):
            return

        suffix = self._suffix_for(trigger)

        # item.main es lo que mostramos y lo que insertamos como "valor"
        
        replacement_token = item

        # reemplaza [trigger ... cursor) por trigger + replacement_token + suffix
        new_text = (
            text[:trigger_pos]
            + trigger
            + replacement_token
            + suffix
            + after
        )

        input_widget.value = new_text

        # cursor justo después de lo insertado (no al final del input)
        new_cursor = trigger_pos + trigger_len + len(replacement_token) + len(suffix)
        input_widget.cursor_position = new_cursor

        # cierra el dropdown
        # self.dismiss()

    # ──────────────────────────────
    # helpers
    # ──────────────────────────────

    def _find_last_trigger(self, before: str) -> tuple[int, int]:
        trigger_pos = -1
        trigger_len = 0

        for t in self._triggers:
            pos = before.rfind(t)
            if pos > trigger_pos:
                trigger_pos = pos
                trigger_len = len(t)

        return trigger_pos, trigger_len

    def _suffix_for(self, trigger: str) -> str:
        cfg = self._resolvers.get(trigger)
        return getattr(cfg, "suffix", "")
