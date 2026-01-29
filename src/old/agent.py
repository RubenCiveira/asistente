from __future__ import annotations

import argparse
import os
from dotenv import load_dotenv
from rich.console import Console

from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM, OllamaEmbeddings

from app.core.runtime import AssistantRuntime
from app.core.base_agent import BaseAgent

from app.tools import fs_read_tool, fs_write_tool

console = Console()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="assistant",
        description="Agent-based assistant (single-shot mode)",
    )

    parser.add_argument(
        "-p",
        "--project-dir",
        required=True,
        help="Directorio base del proyecto (workspace).",
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Mensaje de entrada (una única petición).",
    )

    parser.add_argument(
        "--agents-package",
        default="app.agents",
        help="Paquete Python donde descubrir agentes (por defecto: app.agents).",
    )

    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        raise SystemExit(f"Project dir no existe o no es directorio: {project_dir}")

    llm = OllamaLLM(
        model="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.2
    )

    print(llm.invoke("Resume DDD en 3 puntos"))

if __name__ == "__main__":
    main()
