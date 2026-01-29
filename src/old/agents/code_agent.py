from __future__ import annotations
from app.core.base_agent import BaseAgent
from app.core.types import Action, AgentPlan

class CodeAgent(BaseAgent):
    name = "code"
    type = "code"
    short_description = "Codifica"
    description = "Genera código fuente"

    def plan(self, user_input: str, ctx: ToolContext) -> AgentPlan:
        # Aquí es donde usarías el LLM para generar el plan estructurado.
        # De momento: ejemplo fijo.
        actions = [
            Action(
                tool="fs.read",
                input={"path": "README.md"},
                reason="Necesito contexto del proyecto antes de cambiar nada.",
            )
        ]
        return AgentPlan(agent_name=self.name, actions=actions, notes="Draft plan")
