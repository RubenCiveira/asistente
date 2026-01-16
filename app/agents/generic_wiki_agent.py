from __future__ import annotations
from app.core.base_agent import BaseAgent
from app.core.types import Action, AgentPlan

class GenericWikiAgent(BaseAgent):
    name = "generic_wiki"
    type: str = "general"
    short_description: str = "Generic agent"
    description: str = "Agent for lookup on wikipedia when the user ask for it."

    def plan(self, user_input: str, ctx: ToolContext):
        actions = [
            Action(
                tool="fs.read",
                input={"path": "README.md"},
                reason="Necesito contexto del proyecto antes de cambiar nada.",
            )
        ]
        return AgentPlan(agent_name=self.name, actions=actions, notes="Draft plan")
