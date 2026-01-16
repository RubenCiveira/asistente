from __future__ import annotations

from contextlib import contextmanager

@contextmanager
def openai_usage_callback():
    # Preferido (docs actuales)
    try:
        from langchain_community.callbacks.manager import get_openai_callback  # type: ignore
        with get_openai_callback() as cb:
            yield cb
        return
    except Exception:
        pass

    # Fallback (algunas versiones)
    from langchain.callbacks import get_openai_callback  # type: ignore
    with get_openai_callback() as cb:
        yield cb
