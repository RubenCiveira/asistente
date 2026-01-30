"""Token-aware autocomplete overlay for Textual inputs.

Extends :class:`~textual_autocomplete.AutoComplete` so that completions
replace only the active token (the text between the last trigger character
and the cursor) rather than the entire input value.  The dropdown is
positioned above the cursor to avoid overlapping with the chat area.
"""

from __future__ import annotations

from typing import Mapping, Any, Iterable
from textual.geometry import Offset, Region, Spacing

from textual_autocomplete import AutoComplete
from textual_autocomplete.fuzzy_search import FuzzySearch
from textual_autocomplete._autocomplete import TargetState

from app.context.keywords import Keywords


class TokenFuzzySearch(FuzzySearch):
    """Fuzzy search that bypasses query filtering.

    Because the candidate list is already filtered by the completion
    provider, this implementation always returns a perfect score so that
    every candidate supplied by the provider appears in the dropdown.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def match(self, query: str, candidate: str) -> tuple[float, Sequence[int]]:
        """Return a perfect match score regardless of *query*."""
        return super().match(candidate, candidate)


class TokenAwareAutoComplete(AutoComplete):
    """AutoComplete subclass that filters and inserts using only the active token.

    Instead of replacing the entire input value on completion, this class
    locates the trigger character preceding the cursor and replaces only
    the token between the trigger and the cursor position.

    Args:
        keywords: :class:`~app.context.keywords.Keywords` instance for
            trigger detection.
        resolvers: Mapping from trigger strings to provider objects.  The
            provider may optionally expose a ``suffix`` attribute that is
            appended after the completed text.
    """

    def __init__(self, *args, keywords: Keywords, resolvers: Mapping[str, Any], **kwargs):
        """Initialise with trigger resolvers and keyword helper.

        Args:
            keywords: Keywords instance used to locate triggers.
            resolvers: Mapping of trigger string to provider/config object.
        """
        super().__init__(*args, **kwargs)
        self._fuzzy_search = TokenFuzzySearch()
        self._keywords = keywords
        self._resolvers = resolvers

    def apply_completion(self, item: DropdownItem, state: TargetState) -> None:
        """Replace only the active token with the selected completion item.

        Locates the trigger preceding the cursor, computes the token span,
        and rewrites just that portion of the input, leaving text before
        the trigger and after the cursor untouched.

        Args:
            item: The selected dropdown item.
            state: Current autocomplete target state.
        """
        input_widget = self.target  # el Input target
        text = state.text or ""
        cursor = state.cursor_position
        before = text[:cursor]
        after = text[cursor:]

        trigger_pos, trigger_len, trigger_char = self._keywords.find_last_trigger(before)
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
        """Position the dropdown above the cursor, constrained to the screen.

        Calculates available vertical space above the cursor and sizes
        the dropdown accordingly so it does not overflow the visible area.
        """
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
        """Return the suffix string to append after a completion for *trigger*.

        If the resolver for *trigger* has a ``suffix`` attribute it is used;
        otherwise an empty string is returned.
        """
        cfg = self._resolvers.get(trigger)
        return getattr(cfg, "suffix", "")

    # def _find_last_trigger(self, before: str) -> tuple[int, int, str | None]:
    #     trigger_pos = -1
    #     trigger_len = 0
    #     trigger_char = None

    #     for t in self._triggers:
    #         pos = before.rfind(t)
    #         if pos == -1:
    #             continue

    #         # validar contexto previo
    #         if pos > 0:
    #             prev = before[pos - 1]
    #             if not (prev.isspace() or prev in self.VALID_TRIGGER_PREFIXES):
    #                 continue

    #         if pos > trigger_pos:
    #             trigger_pos = pos
    #             trigger_len = len(t)
    #             trigger_char = t

    #     return trigger_pos, trigger_len, trigger_char