"""Workspace grouping backed by ``workspace.json`` inside the workspace root.

A workspace is a named directory that aggregates several projects.  The
:class:`Workspace` dataclass handles loading and persisting the workspace
manifest and tracking which project is currently active.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Set


@dataclass
class Workspace:
    """A named directory that groups related projects.

    Attributes:
        root_dir: Absolute path to the workspace root.
        name: Human-readable name (defaults to the directory name).
        created_at: ISO-8601 creation timestamp.
        projects: Resolved paths of projects belonging to this workspace.
        active_project: Path of the currently selected project, or ``None``.
        topics: Topic names included in this workspace.
    """

    root_dir: Path
    name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    projects: List[Path] = field(default_factory=list)
    active_project: Optional[Path] = None
    topics: List[str] = field(default_factory=list)

    @property
    def file(self) -> Path:
        """Return the path to ``workspace.json`` inside the workspace root."""
        return self.root_dir / "workspace.json"

    @classmethod
    def load_or_create(
        cls, root_dir: Path, valid_topics: Optional[Set[str]] = None
    ) -> "Workspace":
        """Load an existing workspace from *root_dir* or create a new one.

        The directory is created when it does not exist.  If a
        ``workspace.json`` file is found it is read; otherwise a fresh
        workspace is persisted and returned.

        When *valid_topics* is provided, any topic name not present in the
        set is removed and the manifest is re-saved.

        Args:
            root_dir: Path to the workspace directory.
            valid_topics: Optional set of topic names considered valid.

        Returns:
            A ``Workspace`` instance populated from disk or with defaults.
        """
        root_dir.mkdir(parents=True, exist_ok=True)
        file = root_dir / "workspace.json"

        if file.exists():
            data = json.loads(file.read_text())
            projects = [Path(p) for p in data.get("projects", [])]
            active_project = Path(data["active_project"]) if data.get("active_project") else None
            topics = data.get("topics", [])

            ws = cls(
                root_dir=root_dir,
                name=data.get("name", root_dir.name),
                created_at=data.get("created_at"),
                projects=projects,
                active_project=active_project,
                topics=topics,
            )

            if valid_topics is not None:
                pruned = [t for t in ws.topics if t in valid_topics]
                if len(pruned) != len(ws.topics):
                    ws.topics = pruned
                    ws.save()

            return ws

        ws = cls(root_dir=root_dir, name=root_dir.name)
        ws.save()
        return ws

    def add_project(self, project_dir: Path) -> None:
        """Register a project directory with this workspace.

        The path is resolved to an absolute path.  Duplicates are ignored.
        The workspace manifest is saved after every call.

        Args:
            project_dir: Path to the project directory to add.
        """
        project_dir = project_dir.expanduser().resolve()
        if project_dir not in self.projects:
            self.projects.append(project_dir)
        self.save()

    def set_active_project(self, project_dir: Path) -> None:
        """Mark *project_dir* as the active project and register it.

        Delegates to :meth:`add_project` to ensure the project is part of
        the workspace.

        Args:
            project_dir: Path to the project directory.
        """
        project_dir = project_dir.expanduser().resolve()
        self.active_project = project_dir
        self.add_project(project_dir)

    def save(self, valid_topics: Optional[Set[str]] = None) -> None:
        """Persist the workspace manifest to ``workspace.json``.

        When *valid_topics* is provided, any topic name not present in the
        set is removed before writing.

        Args:
            valid_topics: Optional set of topic names considered valid.
        """
        if valid_topics is not None:
            self.topics = [t for t in self.topics if t in valid_topics]

        self.file.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "created_at": self.created_at,
                    "projects": [str(p) for p in self.projects],
                    "active_project": str(self.active_project) if self.active_project else None,
                    "topics": self.topics,
                },
                indent=2,
            )
        )
