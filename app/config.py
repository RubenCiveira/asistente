from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import json


def default_config_path() -> Path:
    return Path.home() / ".config" / "asistente" / "asistente.json"

def default_workspaces_dir() -> Path:
    return Path.home() / ".config" / "asistente" / "workspaces"

@dataclass
class AppConfig:
    config_path: Path
    active_workspace: Optional[Path] = None
    recent_workspaces: List[Path] = field(default_factory=list)
    sessions: List[Dict[str, Optional[str]]] = field(default_factory=list)
    active_session_index: int = 0

    # ---------- load / save ----------

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        path = path or default_config_path()

        if not path.exists():
            return cls(config_path=path)

        data = json.loads(path.read_text())

        return cls(
            config_path=path,
            active_workspace=Path(data["active_workspace"]) if data.get("active_workspace") else None,
            recent_workspaces=[Path(p) for p in data.get("recent_workspaces", [])],
            sessions=data.get("sessions", []),
            active_session_index=data.get("active_session_index", 0),
        )

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "active_workspace": str(self.active_workspace) if self.active_workspace else None,
            "recent_workspaces": [str(p) for p in self.recent_workspaces],
            "sessions": self.sessions,
            "active_session_index": self.active_session_index,
        }

        self.config_path.write_text(json.dumps(payload, indent=2))

    # ---------- dominio ----------

    def set_active_workspace(self, path: Path) -> None:
        path = path.resolve()

        self.active_workspace = path

        if path in self.recent_workspaces:
            self.recent_workspaces.remove(path)

        self.recent_workspaces.insert(0, path)

        # opcional: limitar tamaño
        self.recent_workspaces = self.recent_workspaces[:10]
