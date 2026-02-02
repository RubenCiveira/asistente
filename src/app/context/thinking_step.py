from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

@dataclass(frozen=True)
class ThinkingStep:
    action: str
    invoke: Callable[[], ThinkingResult|str]
    next: Optional[Callable[[ThinkingResult], "ThinkingStep"]] = None

@dataclass(frozen=True)
class ThinkingResult:
    response: str
    context: Optional[str] = None
