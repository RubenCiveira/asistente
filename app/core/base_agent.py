from __future__ import annotations

import json
import os

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.types import Action, AgentPlan, ReviewDecision, ExecutionResult, ToolContext
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
        self._prompts_cache: Dict[str, Dict[str, str]] = {}  # lang -> prompts

    @abstractmethod
    def plan(self, user_input: str, ctx: ToolContext) -> AgentPlan:
        ...

    def review(self, action: Action, ctx: ToolContext) -> ReviewDecision:
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
            out = tool_fn(action.input, ctx)
            return ExecutionResult(action=action, ok=True, output=out)
        except Exception as e:
            return ExecutionResult(action=action, ok=False, error=str(e))

    def get_lang(self, ctx: Optional[ToolContext] = None) -> str:
        if ctx and getattr(ctx, "lang", None):
            return ctx.lang
        return "en"

    def prompts(self, ctx: Optional[ToolContext] = None) -> Dict[str, str]:
        lang = self.get_lang(ctx)
        current = self._load_prompts_for_lang(lang)
        if current:
            return current

        if lang != "en":
            fallback = self._load_prompts_for_lang("en")
            if fallback:
                return fallback

        return {}

    def prompt(self, key: str, ctx: Optional[ToolContext] = None, **vars: Any) -> str:
        pr = self.prompts(ctx)
        template = pr.get(key)

        if template is None and self.get_lang(ctx) != "en":
            # fallback explícito al prompt en inglés si no existe en el idioma actual
            template = self._load_prompts_for_lang("en").get(key)

        if template is None:
            raise KeyError(f"Prompt key not found: {self.name}:{key}")

        try:
            return template.format(**vars)
        except KeyError as e:
            raise KeyError(f"Missing template var {e} for prompt {self.name}:{key}") from e

    def _i18n_dir(self) -> str:
        """
        Directorio de i18n relativo al fichero base_agent.py:

        app/core/base_agent.py
        -> app/agents/i18n
        """
        core_dir = os.path.dirname(os.path.abspath(__file__))          # .../app/core
        app_dir = os.path.dirname(core_dir)                             # .../app
        return os.path.join(app_dir, "agents", "i18n")                   # .../app/agents/i18n

    def _prompts_path(self, lang: str) -> str:
        filename = f"{self.name}.prompts.{lang}.json"
        return os.path.join(self._i18n_dir(), filename)

    def _load_prompts_for_lang(self, lang: str) -> Dict[str, str]:
        if lang in self._prompts_cache:
            return self._prompts_cache[lang]

        path = self._prompts_path(lang)
        if not os.path.exists(path):
            self._prompts_cache[lang] = {}
            return {}

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid prompts file (expected object/dict): {path}")

        # Asegura que todo es string
        prompts: Dict[str, str] = {}
        for k, v in data.items():
            if isinstance(v, str):
                prompts[k] = v

        self._prompts_cache[lang] = prompts
        return prompts