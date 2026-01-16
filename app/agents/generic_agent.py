from __future__ import annotations
from app.core.base_agent import BaseAgent
from app.core.types import Action, AgentPlan

class GenericAgent(BaseAgent):
    name = "generic"
    type: str = "general"
    short_description: str = "Generic agent"
    description: str = "Generic agent with no specific capabilities."

    def can_handle(self, intention: str) -> bool:
        return True

    def plan(self, user_input: str, intention: str):
        actions = [
            Action(
                tool="fs.read",
                input={"path": "README.md"},
                reason="Necesito contexto del proyecto antes de cambiar nada.",
            )
        ]
        return AgentPlan(intention=intention, agent_name=self.name, actions=actions, notes="Draft plan")
