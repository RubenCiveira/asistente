from textual_autocomplete import DropdownItem

class ContextProvider:
    """
    '@' → referencias de contexto (archivos, agentes, recursos)
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
        # dummy por ahora
        items = [
            "README.md",
            "src/",
            "project.json",
            "agent:planner",
            "agent:executor",
        ]
        if prefix.startswith("src/"):
            items = items + [ prefix + "golo/" ]
        return [
            DropdownItem(
                main=f"{item}",
                prefix="📎 ",
            )
            for item in items
            if item.startswith(prefix)
        ]
