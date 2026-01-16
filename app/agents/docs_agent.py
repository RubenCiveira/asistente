from __future__ import annotations
from app.core.base_agent import BaseAgent
from app.core.types import Action, AgentPlan


class DocsAgent(BaseAgent):
    name = "docs"
    type = "docs"
    short_description = "Genera y mejora documentación"
    description = "Mejora README, documentación técnica, guías de uso, changelogs..."
    
    def can_handle(self, intention: str) -> bool:
        return intention == "docs"

    def plan(self, user_input: str, intention: str) -> AgentPlan:
        return AgentPlan(
            intention=intention,
            agent_name=self.name,
            actions=[
                Action(tool="fs.read", input={"path": "README.md"}, reason="Revisar doc actual"),
            ],
            notes="Docs plan",
        )
