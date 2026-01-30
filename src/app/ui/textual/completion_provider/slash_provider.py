from textual_autocomplete import DropdownItem

class SlashCommandProvider:
    """
    '/' → comandos explícitos del sistema / agente
    """

    def __call__(self, prefix: str) -> list[DropdownItem]:
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
