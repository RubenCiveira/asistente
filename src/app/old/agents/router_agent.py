from __future__ import annotations
from typing import Any, Dict, List

import json

from app.core.base_agent import BaseAgent
from app.core.types import AgentPlan
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage,HumanMessage

class DetectIntentionResult(BaseModel):
    intention: str = Field(..., description="Chosen category type")

class SelectAgentResult(BaseModel):
    agent: str = Field(..., description="Chosen agent name")

class RouterAgent(BaseAgent):
    name = "router"
    type = "router"
    short_description = "Selects agent category and agent"
    description = "Determines user intention and selects the best agent to handle the request."

    def can_handle(self, intention: str) -> bool:
        return intention == "router"

    def detect_intention(self, user_input: str, agents: List[BaseAgent], ctx: ToolContext) -> List[BaseAgent]:
        categories = self._build_intentions_catalog( agents )
        categories_text = "\n".join([f"- {k}: {v}" for k, v in categories.items()])
        sys = self.prompt("select_type_system", ctx)
        usr = self.prompt("select_type_user", ctx, user_input=user_input, categories=categories_text)

        llm_struct = self.llm.with_structured_output(DetectIntentionResult)

        result: DetectIntentionResult = llm_struct.invoke([
            SystemMessage(content=sys),
            HumanMessage(content=usr),
        ])
        chosen_type = (result.intention or "").strip()
        # fallback si el tipo no es válido
        if chosen_type not in categories:
            chosen_type = "general"
        # filtrar agentes por tipo
        filtered = [a for a in agents if getattr(a, "type", "general") == chosen_type]

        # fallback si no hay agentes para ese tipo (por ejemplo, "general")
        if not filtered and chosen_type != "general":
            filtered = [a for a in agents if getattr(a, "type", "general") == "general"]

        # último fallback: si no hay "general", devuelve todos menos router/review
        if not filtered:
            filtered = [a for a in agents if a.name not in ("router", "review")]

        ctx.tracer.info(f"Detected intention/type: {chosen_type}")
        ctx.tracer.data("Candidate agents", [a.name for a in filtered])

        return filtered

    def select_agent_in_type(self, user_input: str, candidates: List[BaseAgent], ctx: ToolContext) -> BaseAgent:
        candidates_text = "\n".join([
            f"- {a.name}: {a.description}"
            for a in candidates
        ])

        sys = self.prompt("select_agent_system", ctx)
        usr = self.prompt("select_agent_user", ctx, user_input=user_input, candidates=candidates_text)

        llm_struct = self.llm.with_structured_output(SelectAgentResult)

        result: SelectAgentResult = llm_struct.invoke([
            SystemMessage(content=sys),
            HumanMessage(content=usr),
        ])

        chosen_name = result.agent
        by_name = {a.name: a for a in candidates}

        # fallback
        chosen = by_name.get(chosen_name) or candidates[0]

        ctx.tracer.info(f"Selected agent: {chosen.name}")
        return chosen

    def plan(self, user_input: str) -> AgentPlan:
        # No planifica acciones: solo determina intención.
        return AgentPlan(agent_name="router", actions=[], notes="Router does not plan")

    def _build_intentions_catalog(self, agents: List[BaseAgent]) -> dict[str, str]:
        categories: dict[str, str] = {}

        for agent in agents:
            if agent.name in ("router", "review"):
                continue

            # si varios agentes comparten tipo, nos quedamos con el primer short_description
            categories.setdefault(agent.type, agent.short_description)

        categories.setdefault("general", "General assistant tasks / fallback")
        return categories