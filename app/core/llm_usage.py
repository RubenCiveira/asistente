from __future__ import annotations

from contextlib import contextmanager
from typing import Optional


@contextmanager
def openai_usage_callback():
    """
    Devuelve un callback (cb) con:
      - cb.prompt_tokens
      - cb.completion_tokens
      - cb.total_tokens
      - cb.total_cost

    Si no está disponible (p.ej. falta langchain-community), yield None.
    """
    try:
        from langchain_community.callbacks.manager import get_openai_callback  # type: ignore
    except Exception:
        yield None
        return

    with get_openai_callback() as cb:
        yield cb
