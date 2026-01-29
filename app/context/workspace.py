import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Workspace:
    root_dir: Path
    name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def file(self) -> Path:
        return self.root_dir / "workspace.json"

    @classmethod
    def load_or_create(cls, root_dir: Path) -> "Workspace":
        root_dir.mkdir(parents=True, exist_ok=True)
        file = root_dir / "workspace.json"

        if file.exists():
            data = json.loads(file.read_text())
            return cls(
                root_dir=root_dir,
                name=data.get("name", root_dir.name),
                created_at=data.get("created_at"),
            )

        ws = cls(root_dir=root_dir, name=root_dir.name)
        ws.save()
        return ws

    def save(self) -> None:
        self.file.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "created_at": self.created_at,
                },
                indent=2,
            )
        )
