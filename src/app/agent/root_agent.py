from langchain_ollama import OllamaLLM
from dataclasses import dataclass
from functools import partial
from app.config import AppConfig
from app.rag.project_context import ProjectContextRetriever

@dataclass(frozen=True)
class Step:
    action: str
    invoke: Callable[[], Any]

class RootAgent:
    def __init__(self, config: AppConfig):
        self.llm = OllamaLLM(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.2
        )
        self.config = config

    def execute(self, msg: str) -> Step:
        return Step("thinking", lambda: self._run(msg))
    
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
    
