import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List


@dataclass
class Workspace:
    root_dir: Path
    name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    projects: List[Path] = field(default_factory=list)

    @property
    def file(self) -> Path:
        return self.root_dir / "workspace.json"

    @classmethod
    def load_or_create(cls, root_dir: Path) -> "Workspace":
        root_dir.mkdir(parents=True, exist_ok=True)
        file = root_dir / "workspace.json"

        if file.exists():
            data = json.loads(file.read_text())
            projects = [Path(p) for p in data.get("projects", [])]
            return cls(
                root_dir=root_dir,
                name=data.get("name", root_dir.name),
                created_at=data.get("created_at"),
                projects=projects,
            )

        ws = cls(root_dir=root_dir, name=root_dir.name)
        ws.save()
        return ws

    def add_project(self, project_dir: Path) -> None:
        project_dir = project_dir.expanduser().resolve()
        if project_dir not in self.projects:
            self.projects.append(project_dir)
            self.save()

    def save(self) -> None:
        self.file.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "created_at": self.created_at,
                    "projects": [str(p) for p in self.projects],
                },
                indent=2,
            )
        )
