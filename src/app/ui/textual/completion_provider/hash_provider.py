from textual_autocomplete import DropdownItem

class SemanticProvider:
    """
    '#' → entidades semánticas (clases, dominios, conceptos)
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
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
