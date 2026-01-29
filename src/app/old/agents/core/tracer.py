from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console


@dataclass
class Tracer:
    console: Console
    enabled: bool = True

    def info(self, msg: str) -> None:
        if self.enabled:
            self.console.print(f"[cyan]INFO[/cyan] {msg}")

    def warn(self, msg: str) -> None:
        if self.enabled:
            self.console.print(f"[yellow]WARN[/yellow] {msg}")

    def error(self, msg: str) -> None:
        if self.enabled:
            self.console.print(f"[red]ERROR[/red] {msg}")

    def step(self, title: str) -> None:
        if self.enabled:
            self.console.print(f"\n[bold magenta]▶ {title}[/bold magenta]")

    def data(self, label: str, obj: Any) -> None:
        if self.enabled:
            self.console.print(f"[bold]{label}:[/bold] {obj}")
