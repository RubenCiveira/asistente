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

from app.ui.console.form import ConsoleFormRenderer

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
    schema = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "description": "Directorios a analizar",
                "minItems": 1,
                "maxItems": 10,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    # path "simple": evita espacios raros; permite / . _ - letras números
                    "pattern": r"^[a-zA-Z0-9._/\-]+$",
                },
            },
            "repo_url": {
                "type": "string",
                "description": "Git repository URL (https://... o git@...)",
                # Valida URLs tipo http(s) y ssh (simplificado)
                "pattern": r"^(https?://|git@).+",
                "minLength": 8,
                "maxLength": 300,
            },
            "lang": {
                "type": "string",
                "enum": ["es", "en"],
                "default": "es",
                "description": "Idioma principal",
            },
            "mode": {
                "oneOf": [
                    {"const": "generic", "title": "Uso general"},
                    {"const": "coding", "title": "Programación"},
                    {"const": "reasoning", "title": "Razonamiento"},
                ],
                "default": "generic",
            },
            "features": {
                "type": "array",
                "items": {
                    "oneOf": [
                        {"const": "lint", "title": "Linting"},
                        {"const": "tests", "title": "Tests"},
                        {"const": "docs", "title": "Documentación"},
                    ]
                },
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
            },
            "branch": {
                "type": "string",
                "default": "main",
                # muy simplificado pero útil: evita espacios y caracteres peligrosos
                "pattern": r"^[A-Za-z0-9._/\-]+$",
                "minLength": 1,
                "maxLength": 120,
            },
            "private": {
                "type": "boolean",
                "default": False,
            },
            "repo_token": {
                "type": "string",
                "description": "Token de acceso si el repo es privado",
                "minLength": 10,
                "maxLength": 200,
            },
            "depth": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 50,
            },
        },
        "required": ["repo_url"],

        # --------------------------
        # Validación cruzada (pro)
        # --------------------------
        "allOf": [
            # Si private=true, exigir repo_token
            {
                "if": {
                    "properties": {"private": {"const": True}},
                    "required": ["private"],
                },
                "then": {"required": ["repo_token"]},
            },

            # Si mode=coding, exigir que features contenga "tests"
            # (JSON Schema 2020-12: contains)
            {
                "if": {
                    "properties": {"mode": {"const": "coding"}},
                    "required": ["mode"],
                },
                "then": {
                    "properties": {
                        "features": {
                            "contains": {"const": "tests"}
                        }
                    }
                },
            },

            # Ejemplo de restricción: si lang=en, no permitir mode=reasoning
            {
                "if": {
                    "properties": {"lang": {"const": "en"}},
                    "required": ["lang"],
                },
                "then": {
                    "not": {
                        "properties": {"mode": {"const": "reasoning"}},
                        "required": ["mode"],
                    }
                },
            },
        ],
    }


    form = ConsoleFormRenderer()
    data = form.ask_form(schema)

    print("\n✅ Result:")
    print(data)
def ask_main():
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
