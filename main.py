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


def oldmain(): 
    # LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.2,
    )

    llm 

    runtime = AssistantRuntime(
        llm=llm,
        project_dir=project_dir,
        agents_package=args.agents_package,
    )

    # Tools
    runtime.register_tool("fs.read", fs_read_tool)
    runtime.register_tool("fs.write", fs_write_tool)

    # Agents discovery
    runtime.discover_agents(BaseAgent)

    results = runtime.run(args.input)

    # Salida
    for r in results:
        if r.ok:
            console.print(f"[green]OK[/green] {r.action.tool}")
            console.print(r.output)
        else:
            console.print(f"[red]ERR[/red] {r.action.tool}: {r.error}")


if __name__ == "__main__":
    main()
