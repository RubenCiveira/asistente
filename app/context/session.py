from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.context.workspace import Workspace
from app.context.project import Project


def _new_session_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Session:
    id: str = field(default_factory=_new_session_id)
    workspace: Optional[Workspace] = None
    project: Optional[Project] = None
