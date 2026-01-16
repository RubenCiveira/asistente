from __future__ import annotations
from typing import Any, Dict, List

from app.core.base_agent import BaseAgent
from app.core.types import AgentPlan
from langchain_core.messages import HumanMessage

class RouterAgent(BaseAgent):
    name = "router"

    def can_handle(self, intention: str) -> bool:
        return intention == "router"

    def detect_intention(self, user_input: str, available_agents: List[str]) -> str:
        # Simplificación inicial: reglas rápidas.
        # Luego lo migras a LLM con un prompt y clasificación.
        response = self.llm.invoke([HumanMessage(content=user_input)])
        print( "La respuesta es " + response.content );
        text = user_input.lower()
        if "document" in text or "readme" in text:
            return "docs"
        if "test" in text or "refactor" in text or "code" in text:
            return "code"
        return "general"

    def select_agent(self, intention: str, agents: Dict[str, BaseAgent]) -> str:
        # Si existe uno que can_handle, úsalo.
        for name, agent in agents.items():
            if name == "router":
                continue
            if agent.can_handle(intention):
                return name
        return "code" if "code" in agents else list(agents.keys())[0]

    def plan(self, user_input: str, intention: str) -> AgentPlan:
        # No planifica acciones: solo determina intención.
        return AgentPlan(intention="router", agent_name="router", actions=[], notes="Router does not plan")
