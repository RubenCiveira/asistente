from __future__ import annotations

from typing import Mapping, Any, Iterable
from textual.geometry import Offset, Region, Spacing

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

    # ITEM_HEIGHT = 1
    # BORDER = 2
    # PADDING = 1

    VALID_TRIGGER_PREFIXES = {" ", "\t", "\n", "(", "[", "{", "<"}

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

        trigger_pos, trigger_len, trigger_char = self._find_last_trigger(before)
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

    def _align_to_target(self) -> None:
        x, y = self.target.cursor_screen_offset
        dropdown = self.option_list

        # espacio disponible hacia arriba
        available_above = y - self.screen.scrollable_content_region.y

        # número máximo de filas que caben
        max_rows = max(1, available_above)

        # permitir crecer hasta ahí
        dropdown.styles.max_height = max_rows

        width, height = dropdown.outer_size

        region = Region(
            x - 1,
            y - height,
            width,
            height,
        )

        x, y, _, _ = region.constrain(
            "inside",
            "none",
            Spacing.all(0),
            self.screen.scrollable_content_region,
        )

        self.absolute_offset = Offset(x, y)

    # ──────────────────────────────
    # helpers
    # ──────────────────────────────

    def _suffix_for(self, trigger: str) -> str:
        cfg = self._resolvers.get(trigger)
        return getattr(cfg, "suffix", "")

    def _find_last_trigger(self, before: str) -> tuple[int, int, str | None]:
        trigger_pos = -1
        trigger_len = 0
        trigger_char = None

        for t in self._triggers:
            pos = before.rfind(t)
            if pos == -1:
                continue

            # validar contexto previo
            if pos > 0:
                prev = before[pos - 1]
                if not (prev.isspace() or prev in self.VALID_TRIGGER_PREFIXES):
                    continue

            if pos > trigger_pos:
                trigger_pos = pos
                trigger_len = len(t)
                trigger_char = t

        return trigger_pos, trigger_len, trigger_char