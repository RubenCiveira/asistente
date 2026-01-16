from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.core.tracer import Tracer

@dataclass
class Action:
    tool: str
    input: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class AgentPlan:
    agent_name: str
    actions: List[Action] = field(default_factory=list)
    notes: str = ""


@dataclass
class ReviewDecision:
    action: Action
    approved: bool
    notes: str = ""
    suggested_fix: Optional[Action] = None


@dataclass
class ExecutionResult:
    action: Action
    ok: bool
    output: Any = None
    error: Optional[str] = None

@dataclass(frozen=True)
class ToolContext:
    project_dir: str
    tracer: Tracer
    lang: str = "en"
