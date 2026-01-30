"""Completion provider for slash (``/``) commands.

Returns system-level commands such as ``workspace``, ``project``, ``open``,
``help`` and ``run`` when the user types ``/`` followed by a prefix.
"""

from textual_autocomplete import DropdownItem


class SlashCommandProvider:
    """Provide autocomplete items for ``/`` slash commands.

    Callable that receives the typed prefix after ``/`` and returns
    matching :class:`DropdownItem` suggestions.
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
        """Return slash-command suggestions matching *prefix*.

        Args:
            prefix: Text typed after the ``/`` trigger.

        Returns:
            A list of matching :class:`DropdownItem` instances.
        """
        commands = [
            "workspace",
            "project",
            "open",
            "help",
            "run",
        ]

        return [
            DropdownItem(
                main=f"{cmd}",
                prefix="⚡ ",
            )
            for cmd in commands
            if cmd.startswith(prefix)
        ]
