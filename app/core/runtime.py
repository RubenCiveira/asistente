from __future__ import annotations
from typing import Dict, List

import os
import uuid

from app.core.registry import discover_agent_classes, ToolRegistry
from app.core.types import AgentPlan, ExecutionResult, ToolContext, Tracer
from app.core.tracer import Tracer
from app.core.costs_store import CostsStore
from app.core.work_lock import WorkLock, WorkLockError
from rich.console import Console

from app.core.llm_usage import openai_usage_callback


class AssistantRuntime:
    def __init__(self, llm, project_dir: str, agents_package: str):
        self.llm = llm
        self.project_dir = project_dir
        self.agents_package = agents_package
        self.registry = ToolRegistry()
        self.tracer = Tracer(console = Console(), enabled=True)
        self.agents: Dict[str, BaseAgent] = {}

        self.work_dir = os.path.join(self.project_dir, ".work")
        self.lock_path = os.path.join(self.work_dir, ".lock")
        self.costs_path = os.path.join(self.work_dir, "costs.jsonl")
        self.costs_store = CostsStore(self.costs_path)

    def register_tool(self, name: str, fn):
        self.registry.register(name, fn)

    def discover_agents(self, base_agent_class):
        classes = discover_agent_classes(self.agents_package, base_agent_class)
        for cls in classes:
            instance = cls(self.llm, self.project_dir, self.registry)
            self.agents[instance.name] = instance

    def run(self, user_input: str) -> List[ExecutionResult]:
        try:
            with WorkLock(self.lock_path):
                return self._run_locked(user_input)
        except WorkLockError as e:
            self.tracer.error(str(e))
            raise

    def _run_locked(self, user_input: str) -> List[ExecutionResult]:
        with openai_usage_callback() as cb:
          result = self._run_accounted(user_input)

        session_id = uuid.uuid4().hex[:12]

        usage = {
            "model": getattr(self.llm, "model_name", None) or getattr(self.llm, "model", None) or "unknown",
            "prompt_tokens": getattr(cb, "prompt_tokens", 0),
            "completion_tokens": getattr(cb, "completion_tokens", 0),
            "total_tokens": getattr(cb, "total_tokens", 0),
            "total_cost_usd": float(getattr(cb, "total_cost", 0.0) or 0.0),
        }
        self.costs_store.add_execution(session_id, usage)
        return result

    def _run_accounted(self, user_input: str) -> List[ExecutionResult]:
        ctx = ToolContext(project_dir=self.project_dir, tracer=self.tracer)

        # 1) Determinar intención y seleccionar agente.
        router = self.agents.get("router")
        if router is None:
            raise RuntimeError("Router agent not registered")

        catalog = self._build_agent_catalog()
        intention = router.detect_intention(user_input, catalog)
        chosen_type = router.select_type(user_input, catalog)
        candidates = catalog.get(chosen_type) or []
        if not candidates:
            chosen_type = "general"
            candidates = catalog.get("general", [])

        chosen_agent_name = router.select_agent_in_type(user_input, candidates)
        # available_agent_names = [k for k in self.agents.keys() if k != "router"]
        # chosen_agent_name = router.select_agent(intention, self.agents)
        agent = self.agents[chosen_agent_name]

        # 2) Ejecutar agente y proponer acciones.
        plan = agent.plan(user_input, intention)


        # 3) Revisar cada acción por los agentes.
        reviewer = self.agents.get("review")
        if reviewer is None:
            raise RuntimeError("Review agent not registered")

        reviewed_actions = []
        for action in plan.actions:
            decision = reviewer.review(action)
            if decision.approved:
                reviewed_actions.append(action)
            elif decision.suggested_fix:
                reviewed_actions.append(decision.suggested_fix)
            else:
                # Acción descartada
                pass

        # 4) Aplicar cada acción por el agente más adecuado.
        results: List[ExecutionResult] = []
        for action in reviewed_actions:
            # Aquí podrías enrutar por tool->agente, o por intención, etc.
            # Por simplicidad: ejecuta el agente elegido.
            results.append(agent.execute(action, ctx))
        return results

    def _build_agent_catalog(self) -> dict:
        catalog = {}
        for a in self.agents.values():
            if a.name in ("router", "review"):
                continue
            catalog.setdefault(a.type, []).append({
                "name": a.name,
                "short": a.short_description,
                "desc": a.description,
            })
        return catalog