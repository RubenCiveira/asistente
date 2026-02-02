import time

import time

from langchain_ollama import OllamaLLM
from app.config import AppConfig
from app.rag.project_context import ProjectContextRetriever
from app.context.thinking_step import ThinkingStep, ThinkingResult, AnstractThinkingStep

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
            return FakeStep(msg, 1)
            # f5 = ThinkingStep("fak5", lambda: self._trap("f5" + msg))
            # f4 = ThinkingStep("fak4", lambda: self._trap("f4" + msg), next = lambda _: self._next(f5))
            # f3 = ThinkingStep("fak3", lambda: self._trap("f3" + msg), next = lambda _: self._next(f4))
            # f2 = ThinkingStep("fak2", lambda: self._trap("f2" + msg), next = lambda _: self._next(f3))
            # f1 = ThinkingStep("fak1", lambda: self._trap("f1" + msg), next = lambda _: self._next(f2))
            # return f1
        if msg.startswith("En contexto"):
            return RagStep(msg, self)
            # return ThinkingStep("lookup rag", 
            #     lambda: self._lookup_lambda(msg),
            #     next = lambda prev: self._ask_context(prev, msg) 
            # )
        return CallStep(msg, self)
        # return ThinkingStep("thinking", lambda: self._run(msg))
    
#     def _next(self, th: ThinkingStep) -> ThinkingStep:
#         return th

#     def _trap(self, msg: str) -> str:
#         time.sleep(2)
#         return msg

#     def _ask_context(self, prev: ThinkingResult, msg: string) -> str:
#         time.sleep(2)
#         context = prev.context or prev.response
#         return ThinkingStep("thinking", lambda: self._run("""
# Usa SOLO el contexto para responder.

# Contexto:
# {context}

# Pregunta: {msg}
# """))

#     def _lookup_lambda(self, msg: str) -> str:
#         time.sleep(2)
#         rag = ProjectContextRetriever(self.config)
#         ctx = rag.get_active_context( msg )
#         # return "EL CONTEXTO ES " + ctx
#         return ThinkingResult("Tengo context " + str(len(ctx)), ctx)

#     def _run(self, msg: str) -> str:
#         return self.llm.invoke( msg )
    

class FakeStep(AnstractThinkingStep):
    def __init__(self, msg, index: int):
        super().__init__("fake " + str(index))
        self.msg = msg
        self.index = index

    def think(self):
        time.sleep(2)
        return "F" + str(self.index) + self.msg

    def and_then(self, prev):
        if self.index < 5:
            return FakeStep(self.msg, self.index + 1)

class RagStep(AnstractThinkingStep):
    def __init__(self, msg: str, root: RootAgent):
        super().__init__("rag")
        self.msg = msg
        self.agent = root
    def think(self):
        time.sleep(2)
        rag = ProjectContextRetriever(self.agent.config)
        ctx = rag.get_active_context( self.msg )
        # return "EL CONTEXTO ES " + ctx
        return ThinkingResult("Tengo context " + str(len(ctx)), ctx)
    def and_then(self, prev):
        time.sleep(2)
        context = prev.context or prev.response
        return CallStep("""
Usa SOLO el contexto para responder.

Contexto:
{context}

Pregunta: {msg}
""", self.agent)

class CallStep(AnstractThinkingStep):
    def __init__(self, msg: str, root: RootAgent):
        super().__init__("thinkg")
        self.msg = msg
        self.agent = root
    def think(self):
        return self.agent.llm.invoke( self.msg )

