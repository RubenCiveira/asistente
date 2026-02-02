from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class ThinkingStep:
    action: str
    invoke: Callable[[], ThinkingResult|str]
    next: Optional[Callable[[ThinkingResult], "ThinkingStep"]] = None

@dataclass(frozen=True)
class ThinkingResult:
    response: str
    context: Optional[str] = None

class AnstractThinkingStep(ABC):
    def __init__(self, action: str):
        self.action = action
        self.invoke = self.think
        self.next = lambda r: self.and_then(r)

    @abstractmethod
    def think(self) -> ThinkingResult | str:
        pass

    def and_then(self, prev: ThinkingResult) -> ThinkingStep | None:
        pass

    # def build(self) -> ThinkingStep:
    #     return ThinkingStep(
    #         action=self.__class__.__name__,
    #         invoke=self.think,
    #         next=lambda r: self.and_then(r).build() if self.and_then(r) else None
    #     )