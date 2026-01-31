from langchain_ollama import OllamaLLM

class RootAgent:
    def execute(self, msg: str) -> str:
        llm = OllamaLLM(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
            temperature=0.2
        )
        return llm.invoke(msg)
