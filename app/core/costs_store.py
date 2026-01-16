from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


def _now_iso() -> str:
    # ISO simple (sin microsegundos) y con zona local (si quieres UTC te lo cambio)
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class CostsStore:
    costs_path: str

    def add_execution(
        self,
        session_id: str,
        usage: Dict[str, Any],
        *,
        project_dir: Optional[str] = None,
        input_text: Optional[str] = None,
        intention: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> None:
        """
        Guarda 1 línea JSON por ejecución.

        usage esperado (ejemplo):
        {
          "prompt_tokens": 100,
          "completion_tokens": 200,
          "total_tokens": 300,
          "total_cost_usd": 0.0012,
          "model": "gpt-4o-mini"
        }
        """
        os.makedirs(os.path.dirname(self.costs_path) or ".", exist_ok=True)

        row: Dict[str, Any] = {
            "ts": time.time(),
            "at": _now_iso(),
            "session_id": session_id,
            "usage": usage,
        }

        # metadata opcional útil para filtrar luego
        if project_dir:
            row["project_dir"] = project_dir
        if input_text:
            row["input_chars"] = len(input_text)
        if intention:
            row["intention"] = intention
        if agent_name:
            row["agent"] = agent_name

        with open(self.costs_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
