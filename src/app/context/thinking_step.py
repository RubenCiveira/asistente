from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

@dataclass(frozen=True)
class ThinkingStep:
    action: str
    invoke: Callable[[], str]
    next: Optional[Callable[[], "ThinkingStep"]] = None
