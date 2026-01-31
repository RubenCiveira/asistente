from langchain_ollama import OllamaLLM
from dataclasses import dataclass
from functools import partial

@dataclass(frozen=True)
class Step:
    action: str
    invoke: Callable[[], Any]

class RootAgent:
    def __init__(self):
        self.llm = OllamaLLM(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.2
        )

    def execute(self, msg: str) -> Step:
        return Step("thinking", lambda: self._run(msg))
    
    def _run(self, msg: str) -> str:
        return self.llm.invoke( msg )
    
