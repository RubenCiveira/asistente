from textual_autocomplete import DropdownItem

class PowerCommandProvider:
    """
    ':' → comandos rápidos tipo consola / vim / power-user
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
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
