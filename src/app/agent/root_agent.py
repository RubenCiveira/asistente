import time

import time

from langchain_ollama import OllamaLLM
from app.config import AppConfig
from app.rag.project_context import ProjectContextRetriever
from app.context.thinking_step import ThinkingStep

class RootAgent:
    def __init__(self, config: AppConfig):
        self.llm = OllamaLLM(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.2
        )
        self.config = config

    def execute(self, msg: str) -> ThinkingStep:
        if msg == "hola":
            f5 = ThinkingStep("fak5", lambda: self._trap("f5" + msg))
            f4 = ThinkingStep("fak4", lambda: self._trap("f4" + msg), next = lambda: self._next(f5))
            f3 = ThinkingStep("fak3", lambda: self._trap("f3" + msg), next = lambda: self._next(f4))
            f2 = ThinkingStep("fak3", lambda: self._trap("f2" + msg), next = lambda: self._next(f3))
            f1 = ThinkingStep("fak1", lambda: self._trap("f1" + msg), next = lambda: self._next(f2))
            return f1
        return ThinkingStep("thinking", lambda: self._run(msg))
    
    def _next(self, th: ThinkingStep) -> ThinkingStep:
        return th

    def _trap(self, msg: str) -> str:
        time.sleep(2)
        return msg

    def _run(self, msg: str) -> str:
        if( msg.startswith("En contexto")):
            rag = ProjectContextRetriever(self.config)
            context = rag.get_active_context( msg )
            prompt = f"""
Usa SOLO el contexto para responder.

Contexto:
{context}

Pregunta: {msg}
"""
            return self.llm.invoke( msg )
        return self.llm.invoke( msg )
    
