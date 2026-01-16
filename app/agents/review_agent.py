from __future__ import annotations
from app.core.base_agent import BaseAgent
from app.core.types import Action, ReviewDecision


class ReviewAgent(BaseAgent):
    name = "review"

    def can_handle(self, intention: str) -> bool:
        return intention == "review"

    def plan(self, user_input: str, intention: str):
        raise NotImplementedError("ReviewAgent no genera planes")

    def review(self, action: Action) -> ReviewDecision:
        # Reglas rápidas para ejemplo
        if action.tool == "fs.write":
            path = action.input.get("path", "")
            if not path:
                return ReviewDecision(action=action, approved=False, notes="Missing path in write action")
            if path.startswith("/"):
                return ReviewDecision(action=action, approved=False, notes="Absolute paths not allowed")
        return ReviewDecision(action=action, approved=True, notes="OK")
