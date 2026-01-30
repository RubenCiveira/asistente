"""Trigger-based keyword utilities for autocomplete.

Provides the :class:`Keywords` helper that identifies trigger characters
(``/``, ``@``, ``:``, ``#``, etc.) inside an input string and determines
whether autocomplete should remain open after a completion is accepted.
"""


class Keywords:
    """Manages trigger characters used to activate autocomplete providers.

    A trigger is a short prefix string (e.g. ``/``, ``@``) that, when typed
    after whitespace or certain punctuation, activates the corresponding
    completion provider.

    Attributes:
        CONTINUE_WRITE_VALID_CHARS: Characters that, when a completion ends
            with one of them, keep the autocomplete dropdown open so the
            user can chain further input.
        VALID_TRIGGER_PREFIXES: Characters allowed immediately before a
            trigger for it to be considered valid context.
    """

    CONTINUE_WRITE_VALID_CHARS = ("/", ":", "#", "@", ".")

    VALID_TRIGGER_PREFIXES = {" ", "\t", "\n", "(", "[", "{", "<"}

    def __init__(self, triggers):
        """Initialise with a list of trigger strings.

        Args:
            triggers: Ordered sequence of trigger strings, typically sorted
                longest-first so multi-character triggers match before
                single-character ones.
        """
        self._triggers = triggers

    def must_continue(self, txt):
        """Return ``True`` if *txt* ends with a character that should keep
        the autocomplete dropdown open.

        Args:
            txt: The text to inspect (usually a completed item label).

        Returns:
            ``True`` when the last character is in
            :attr:`CONTINUE_WRITE_VALID_CHARS`.
        """
        return str(txt).endswith(self.CONTINUE_WRITE_VALID_CHARS)

    def find_last_trigger(self, before: str) -> tuple[int, int, str | None]:
        """Find the rightmost valid trigger in *before*.

        A trigger is considered valid only if it appears at the start of the
        string or is preceded by whitespace / a character in
        :attr:`VALID_TRIGGER_PREFIXES`.

        Args:
            before: The portion of input text to the left of the cursor.

        Returns:
            A three-tuple ``(position, length, trigger)`` where *position*
            is the index of the trigger in *before*, *length* is the trigger
            string length, and *trigger* is the matched string.  When no
            trigger is found ``(-1, 0, None)`` is returned.
        """
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