from typing import Optional

@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Estado funcional
    status: str = "active"  # active | paused | completed

    # Datos propios del proyecto
    metadata: dict = field(default_factory=dict)

    # Enlace a sesiones de chat/agentes
    chat_sessions: List[str] = field(default_factory=list)

    def add_chat_session(self, session_id: str):
        self.chat_sessions.append(session_id)
