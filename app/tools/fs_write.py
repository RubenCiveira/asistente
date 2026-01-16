from __future__ import annotations
import os
from app.core.types import ToolContext


def fs_write_tool(params: dict, ctx: ToolContext) -> dict:
    rel = params.get("path")
    content = params.get("content")

    if not rel:
        raise ValueError("Missing 'path'")
    if content is None:
        raise ValueError("Missing 'content'")

    full = os.path.abspath(os.path.join(ctx.project_dir, rel))

    base = os.path.abspath(ctx.project_dir)
    if not (full == base or full.startswith(base + os.sep)):
        raise ValueError("Path escapes project_dir")

    os.makedirs(os.path.dirname(full) or base, exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)

    return {"ok": True, "path": rel, "bytes": len(content)}
