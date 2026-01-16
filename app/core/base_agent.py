from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.types import Action, AgentPlan, ReviewDecision, ExecutionResult
from app.core.registry import ToolRegistry

class BaseAgent(ABC):
    """
    Todos los agentes reciben:
      - llm (LangChain LLM)
      - project_dir (directorio raíz del proyecto)
      - registry (tool registry)
    """

    name: str = "base"

    def __init__(self, llm: Any, project_dir: str, registry: ToolRegistry):
        self.llm = llm
        self.project_dir = project_dir
        self.registry = registry

    @abstractmethod
    def can_handle(self, intention: str) -> bool:
        ...

    @abstractmethod
    def plan(self, user_input: str, intention: str) -> AgentPlan:
        ...

    def review(self, action: Action) -> ReviewDecision:
        """
        Revisión por defecto: aprobar siempre.
        La idea es que el review real se implemente en ReviewAgent.
        """
        return ReviewDecision(action=action, approved=True, notes="Default approve")

    def execute(self, action: Action, ctx: ToolContext) -> ExecutionResult:
        """
        Ejecuta una acción llamando a la tool.
        """
        try:
            tool_fn = self.registry.get(action.tool)
            out = tool_fn(action.input, ctx)  # ✅ pasar ctx
            return ExecutionResult(action=action, ok=True, output=out)
        except Exception as e:
            return ExecutionResult(action=action, ok=False, error=str(e))
