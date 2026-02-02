"""Application-level configuration persisted as JSON in the user config directory.

The configuration file lives at ``~/.config/asistente/asistente.json`` by
default and stores the active workspace, recent workspace history, open
sessions and the index of the last active session.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


def default_config_path() -> Path:
    """Return the conventional path to the application config file."""
    return Path.home() / ".config" / "asistente" / "asistente.json"


def default_workspaces_dir() -> Path:
    """Return the default directory for workspace storage."""
    return Path.home() / ".config" / "asistente" / "workspaces"


@dataclass
class PostgresRagConfig:
    """PostgreSQL connection parameters for RAG data source.

    Attributes:
        host: Database server hostname.
        port: Database server port.
        database: Database name.
        user: Database user.
        password: Database password.
        table: Table used as the RAG source.
    """

    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = ""
    password: str = ""
    table: str = ""


@dataclass
class Topic:
    """A named data topic used as context source.

    Attributes:
        name: Unique topic identifier.
        type: Topic type (only ``"directory"`` for now).
        path: Filesystem path associated with this topic.
    """

    name: str
    type: str = "directory"
    path: str = ""


@dataclass
class AppConfig:
    """Application configuration backed by a JSON file.

    Attributes:
        config_path: Absolute path to the JSON configuration file.
        active_workspace: Path of the last selected workspace, or ``None``.
        recent_workspaces: Most-recently-used workspace paths (max 10).
        sessions: Serialised session dicts (``id``, ``workspace``, ``project``).
        active_session_index: Index of the last active session in *sessions*.
        postgres_rag: PostgreSQL connection config for RAG.
        topics: List of topic definitions available application-wide.
    """

    config_path: Path
    active_workspace: Optional[Path] = None
    recent_workspaces: List[Path] = field(default_factory=list)
    sessions: List[Dict[str, Optional[str]]] = field(default_factory=list)
    active_session_index: int = 0
    postgres_rag: PostgresRagConfig = field(default_factory=PostgresRagConfig)
    topics: List[Topic] = field(default_factory=list)

    def topic_names(self) -> Set[str]:
        """Return the set of defined topic names."""
        return {t.name for t in self.topics}

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        """Load the configuration from a JSON file.

        If the file does not exist an ``AppConfig`` with default values is
        returned.

        Args:
            path: Explicit config file path.  Falls back to
                :func:`default_config_path` when ``None``.

        Returns:
            A populated ``AppConfig`` instance.
        """
        path = path or default_config_path()

        if not path.exists():
            return cls(config_path=path)

        data = json.loads(path.read_text())

        pg_data = data.get("postgres_rag")
        postgres_rag = PostgresRagConfig(**pg_data) if pg_data else PostgresRagConfig()

        topics = [Topic(**t) for t in data.get("topics", [])]

        return cls(
            config_path=path,
            active_workspace=Path(data["active_workspace"]) if data.get("active_workspace") else None,
            recent_workspaces=[Path(p) for p in data.get("recent_workspaces", [])],
            sessions=data.get("sessions", []),
            active_session_index=data.get("active_session_index", 0),
            postgres_rag=postgres_rag,
            topics=topics,
        )

    def save_topics(self, topics: List[Topic]):
        from app.rag.rag_ingest import RagIngest
        self.topics = topics
        RagIngest(self).ingest()

    def save_rag_connection(self, connection: PostgresRagConfig) -> None:
        from app.rag.postgres_rag_setup import PostgresRagSetup

        PostgresRagSetup(connection).configure()
        self.postgres_rag = connection

    def save(self) -> None:
        """Persist the current configuration to disk as pretty-printed JSON.

        Parent directories are created automatically when they do not exist.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "active_workspace": str(self.active_workspace) if self.active_workspace else None,
            "recent_workspaces": [str(p) for p in self.recent_workspaces],
            "sessions": self.sessions,
            "active_session_index": self.active_session_index,
            "postgres_rag": dataclasses.asdict(self.postgres_rag),
            "topics": [dataclasses.asdict(t) for t in self.topics],
        }

        self.config_path.write_text(json.dumps(payload, indent=2))

    def set_active_workspace(self, path: Path) -> None:
        """Set *path* as the active workspace and prepend it to the recent list.

        Duplicates are removed so the path appears only once (at position 0).
        The recent list is capped at 10 entries.

        Args:
            path: Workspace root directory.
        """
        path = path.resolve()

        self.active_workspace = path

        if path in self.recent_workspaces:
            self.recent_workspaces.remove(path)

        self.recent_workspaces.insert(0, path)

        # opcional: limitar tamaño
        self.recent_workspaces = self.recent_workspaces[:10]
