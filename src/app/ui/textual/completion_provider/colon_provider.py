"""Completion provider for colon (``:``) power-user commands.

Returns quick commands such as ``ws``, ``proj``, ``open``, ``clear`` and
``quit`` when the user types ``:`` followed by a prefix.
"""

from textual_autocomplete import DropdownItem


class PowerCommandProvider:
    """Provide autocomplete items for ``:`` power-user commands.

    Callable that receives the typed prefix after ``:`` and returns
    matching :class:`DropdownItem` suggestions for console-style
    shortcut commands.
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
        """Return power-command suggestions matching *prefix*.

        Args:
            prefix: Text typed after the ``:`` trigger.

        Returns:
            A list of matching :class:`DropdownItem` instances.
        """
        commands = [
            "ws",
            "proj",
            "open",
            "clear",
            "quit",
        ]

        return [
            DropdownItem(
                main=f"{cmd}",
                prefix="⌨️ ",
            )
            for cmd in commands
            if cmd.startswith(prefix)
        ]
