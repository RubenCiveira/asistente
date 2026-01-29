import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class Project:
    id: str
    name: str
    description: str
    status: str

    root_dir: Path
    metadata: Dict[str, Any] = field(default_factory=dict)

    CONFIG_RELATIVE_PATH = Path(".conf/assistants/project.json")

    # --------- carga / guardado ---------

    @classmethod
    def load_or_create(cls, project_dir: Path) -> "Project":
        project_dir = project_dir.expanduser().resolve()
        if not project_dir.is_dir():
            raise NotADirectoryError(
                f"Project directory does not exist: {project_dir}"
            )

        config_path = project_dir / cls.CONFIG_RELATIVE_PATH

        if config_path.exists():
            data = json.loads(config_path.read_text())
            return cls(
                id=data.get("id", str(uuid.uuid4())),
                name=data.get("name", project_dir.name),
                description=data.get("description", ""),
                status=data.get("status", "active"),
                root_dir=project_dir,
                metadata=data.get("metadata", {}),
            )

        prj = cls(
            id=str(uuid.uuid4()),
            name=project_dir.name,
            description="",
            status="active",
            root_dir=project_dir,
        )
        prj.save()
        return prj

    def save(self):
        config_path = self.root_dir / self.CONFIG_RELATIVE_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "metadata": self.metadata,
        }

        config_path.write_text(json.dumps(payload, indent=2))
