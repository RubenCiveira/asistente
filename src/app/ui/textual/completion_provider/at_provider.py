"""Completion provider for at (``@``) context references.

Returns context-reference suggestions such as file names, agent
identifiers and resource paths when the user types ``@`` followed by
a prefix.
"""

from textual_autocomplete import DropdownItem


class ContextProvider:
    """Provide autocomplete items for ``@`` context references.

    Callable that receives the typed prefix after ``@`` and returns
    matching :class:`DropdownItem` suggestions for files, agents and
    other context resources.
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
        """Return context-reference suggestions matching *prefix*.

        Args:
            prefix: Text typed after the ``@`` trigger.

        Returns:
            A list of matching :class:`DropdownItem` instances.
        """
        # dummy por ahora
        items = [
            "README.md",
            "src/",
            "project.json",
            "agent:planner",
            "agent:executor",
        ]
        if prefix.startswith("src/"):
            items = items + [prefix + "golo/"]
        return [
            DropdownItem(
                main=f"{item}",
                prefix="📎 ",
            )
            for item in items
            if item.startswith(prefix)
        ]
