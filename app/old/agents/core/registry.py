from __future__ import annotations

from typing import Any, Callable, Dict, List
from app.core.types import ToolContext

import importlib
import pkgutil


ToolFn = Callable[[dict, ToolContext], Any]

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_names(self) -> List[str]:
        return sorted(self._tools.keys())


def discover_agent_classes(package: str, base_class: Type) -> List[Type]:
    """
    Descubre clases que heredan de base_class dentro de un paquete.
    """
    found: List[Type] = []
    module = importlib.import_module(package)

    for _, modname, _ in pkgutil.iter_modules(module.__path__):
        full = f"{package}.{modname}"
        m = importlib.import_module(full)

        for obj in m.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, base_class) and obj is not base_class:
                found.append(obj)

    return found
