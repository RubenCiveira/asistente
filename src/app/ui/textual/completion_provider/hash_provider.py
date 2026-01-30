"""Completion provider for hash (``#``) semantic entities.

Returns domain entity names such as ``User``, ``Workspace``, ``Project``,
``Agent`` and ``Context`` when the user types ``#`` followed by a prefix.
Matching is case-insensitive.
"""

from textual_autocomplete import DropdownItem


class SemanticProvider:
    """Provide autocomplete items for ``#`` semantic entity references.

    Callable that receives the typed prefix after ``#`` and returns
    matching :class:`DropdownItem` suggestions.  Comparison is
    case-insensitive.
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
        """Return semantic-entity suggestions matching *prefix*.

        Args:
            prefix: Text typed after the ``#`` trigger (case-insensitive).

        Returns:
            A list of matching :class:`DropdownItem` instances.
        """
        entities = [
            "User",
            "Workspace",
            "Project",
            "Agent",
            "Context",
        ]

        return [
            DropdownItem(
                main=f"{name}",
                prefix="🏷 ",
            )
            for name in entities
            if name.lower().startswith(prefix.lower())
        ]
