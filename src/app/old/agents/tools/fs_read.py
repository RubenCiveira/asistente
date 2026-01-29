from __future__ import annotations
import os
from app.core.types import ToolContext


def fs_read_tool(params: dict, ctx: ToolContext) -> dict:
    rel = params.get("path")
    if not rel:
        raise ValueError("Missing 'path'")

    # Normaliza y ancla al project_dir
    full = os.path.abspath(os.path.join(ctx.project_dir, rel))

    # (opcional pero recomendado) evitar path traversal fuera del project_dir
    base = os.path.abspath(ctx.project_dir)
    if not (full == base or full.startswith(base + os.sep)):
        raise ValueError("Path escapes project_dir")

    if not os.path.exists(full):
        return {"ok": False, "error": f"File not found: {rel}"}

    with open(full, "r", encoding="utf-8") as f:
        return {"ok": True, "path": rel, "content": f.read()}
