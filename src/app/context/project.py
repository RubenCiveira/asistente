"""Project metadata backed by a JSON file at ``.conf/assistants/project.json``.

Each project directory contains a small configuration file that stores the
project identity, description, status and arbitrary metadata.  The
:class:`Project` dataclass handles loading and persisting this file.
"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass
class Project:
    """A project with identity and metadata persisted to disk.

    Attributes:
        id: Unique identifier (UUID-4).
        name: Human-readable name (defaults to the directory name).
        description: Free-text project description.
        status: Lifecycle status (e.g. ``"active"``).
        root_dir: Absolute path to the project root directory.
        metadata: Arbitrary key/value pairs stored alongside the project config.
        topics: Topic names included in this project.
    """

    id: str
    name: str
    description: str
    status: str

    root_dir: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)

    CONFIG_RELATIVE_PATH = Path(".conf/assistants/project.json")
    """Relative path from the project root to the configuration file."""

    @classmethod
    def load_or_create(
        cls, project_dir: Path, valid_topics: Optional[Set[str]] = None
    ) -> "Project":
        """Load an existing project from *project_dir* or create a new one.

        The directory is created if it does not exist.  When a configuration
        file is found it is read; otherwise a fresh project with a new UUID
        is persisted and returned.

        When *valid_topics* is provided, any topic name not present in the
        set is removed and the config is re-saved.

        Args:
            project_dir: Path to the project root directory.
            valid_topics: Optional set of topic names considered valid.

        Returns:
            A ``Project`` instance populated from disk or with defaults.
        """
        project_dir = project_dir.expanduser().resolve()
        project_dir.mkdir(parents=True, exist_ok=True)

        config_path = project_dir / cls.CONFIG_RELATIVE_PATH

        if config_path.exists():
            data = json.loads(config_path.read_text())
            topics = data.get("topics", [])

            prj = cls(
                id=data.get("id", str(uuid.uuid4())),
                name=data.get("name", project_dir.name),
                description=data.get("description", ""),
                status=data.get("status", "active"),
                root_dir=project_dir,
                metadata=data.get("metadata", {}),
                topics=topics,
            )

            if valid_topics is not None:
                pruned = [t for t in prj.topics if t in valid_topics]
                if len(pruned) != len(prj.topics):
                    prj.topics = pruned
                    prj.save()

            return prj

        prj = cls(
            id=str(uuid.uuid4()),
            name=project_dir.name,
            description="",
            status="active",
            root_dir=project_dir,
        )
        prj.save()
        return prj

    def save(self, valid_topics: Optional[Set[str]] = None) -> None:
        """Persist the project configuration to disk.

        Creates the parent directories of the config file if they do not
        exist and writes the current state as pretty-printed JSON.

        When *valid_topics* is provided, any topic name not present in the
        set is removed before writing.

        Args:
            valid_topics: Optional set of topic names considered valid.
        """
        if valid_topics is not None:
            self.topics = [t for t in self.topics if t in valid_topics]

        config_path = self.root_dir / self.CONFIG_RELATIVE_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "metadata": self.metadata,
            "topics": self.topics,
        }

        config_path.write_text(json.dumps(payload, indent=2))
