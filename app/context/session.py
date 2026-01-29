from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.context.workspace import Workspace
from app.context.project import Project


@dataclass
class Session:
    id: str
    workspace: Optional[Workspace] = None
    project: Optional[Project] = None
