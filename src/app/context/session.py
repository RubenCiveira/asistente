"""Lightweight session container binding a UUID to an optional workspace and project.

A session represents a single tab in the TUI.  Each session holds references
to the currently selected :class:`Workspace` and :class:`Project`, allowing
multiple independent working contexts to coexist.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.context.workspace import Workspace
from app.context.project import Project


def _new_session_id() -> str:
    """Generate a new UUID-4 string for use as a session identifier."""
    return str(uuid.uuid4())


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
