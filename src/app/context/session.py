"""Lightweight session container binding a UUID to an optional workspace and project.

A session represents a single tab in the TUI.  Each session holds references
to the currently selected :class:`Workspace` and :class:`Project`, allowing
multiple independent working contexts to coexist.
"""

from __future__ import annotations

import uuid
import asyncio

from dataclasses import dataclass, field
import asyncio
from typing import Any, Callable, Optional

from app.agent.root_agent import RootAgent

from app.context.workspace import Workspace
from app.context.project import Project


def _new_session_id() -> str:
    """Generate a new UUID-4 string for use as a session identifier."""
    return str(uuid.uuid4())

@dataclass(frozen=True)
class CallbackPill:
    description: str
    callback: Callable[[], Any]

@dataclass(frozen=True)
class MessageKind:
    actor: str
    msg: str

@dataclass
class Session:
    """In-memory session record tying a unique identifier to an active workspace and project.

    A new UUID is generated automatically when no *id* is supplied.

    Attributes:
        id: Unique session identifier (UUID-4 by default).
        workspace: Currently selected workspace, or ``None``.
        project: Currently selected project, or ``None``.
    """

    id: str = field(default_factory=_new_session_id)
    workspace: Optional[Workspace] = None
    project: Optional[Project] = None
    agent: RootAgent = field(default_factory=RootAgent)
    asking: bool = False
    question: str = ""
    messages: list[MessageKind] = field(default_factory=list)
    _listeners: list[Callable[["Session"], None]] = field(default_factory=list, init=False, repr=False)

    def subscribe(self, listener: Callable[["Session"], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[["Session"], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener(self)

    async def ask(self, text: str) -> CallbackPill | None:
        text = text.strip()
        if not text:
            return None
        if self.asking:
            return None
        self.messages.append(MessageKind("user", text))
        self.question = text
        self.asking = True
        self._notify()
        return CallbackPill("thinking", self._run)

    async def _run(self) -> None:
        try:
            response = await asyncio.to_thread(self.agent.execute, self.question)
        except Exception as exc:
            response = f"Error: {exc}"
        self.messages.append(MessageKind("assistant", response))
        self.asking = False
        self.question = ""
        self._notify()
