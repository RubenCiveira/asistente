from typing import Dict, Any

@dataclass
class Workspace:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    projects: List["Project"] = field(default_factory=list)

    def add_project(self, project: "Project"):
        self.projects.append(project)

    def get_project(self, project_id: str) -> "Project | None":
        return next(
            (p for p in self.projects if p.id == project_id),
            None,
        )
