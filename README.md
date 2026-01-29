# Asistente

Multi-agent AI assistant framework built on LangChain. Routes user requests to
specialized agents that plan, review and execute tasks using registered tools.

## Features

- **Router-based architecture** — a router agent analyses the user's intent and
  delegates to the best specialist (code generation, documentation, tests, etc.).
- **Plan → Review → Execute pipeline** — every action is planned by an agent,
  validated by a review agent and only then executed.
- **JSON-Schema-driven forms** — both the console (prompt_toolkit) and the TUI
  (Textual) interfaces render forms dynamically from JSON Schema with
  incremental validation.
- **Tool registry** — tools are registered at runtime; built-in tools provide
  sandboxed file-system read/write access.
- **Cost tracking** — token usage and costs are logged per session in JSONL
  format.
- **i18n prompts** — agent prompts are stored as JSON files and resolved by
  language at runtime.

## Requirements

- Python >= 3.12
- A running [Ollama](https://ollama.com) instance **or** an OpenAI API key.

## Quick start

```bash
# Clone
git clone https://github.com/RubenCiveira/asistente.git
cd asistente

# Install
make build

# Copy and edit environment variables
cp .env.example .env        # add your OPENAI_API_KEY or configure Ollama

# Run the TUI
python window.py

# Run the console form demo
python main.py -p . -i "hello"
```

## Makefile targets

| Target        | Description                                      |
|---------------|--------------------------------------------------|
| `make build`  | Create virtualenv and install all dependencies.  |
| `make test`   | Run the test suite with pytest.                  |
| `make lint`   | Run ruff linter.                                 |
| `make format` | Auto-format code with ruff.                      |
| `make clean`  | Remove virtualenv and cached files.              |

## Project layout

```
asistente/
├── agent.py              # Single-shot CLI entry point
├── main.py               # Interactive console mode
├── window.py             # Textual TUI entry point
├── app/
│   ├── core/
│   │   ├── base_agent.py     # Abstract agent base class
│   │   ├── runtime.py        # Orchestration engine
│   │   ├── registry.py       # Tool / agent registry
│   │   ├── types.py          # Shared data classes
│   │   ├── tracer.py         # Rich console logger
│   │   ├── costs_store.py    # JSONL cost tracker
│   │   ├── work_lock.py      # File-based mutex
│   │   └── llm_usage.py      # OpenAI callback wrapper
│   ├── agents/               # Agent implementations (auto-discovered)
│   │   ├── router_agent.py
│   │   ├── review_agent.py
│   │   ├── generic_agent.py
│   │   ├── code_agent.py
│   │   ├── code_test_agent.py
│   │   ├── docs_agent.py
│   │   ├── docs_uml_agent.py
│   │   └── generic_wiki_agent.py
│   ├── tools/
│   │   ├── fs_read.py        # Sandboxed file read
│   │   └── fs_write.py       # Sandboxed file write
│   ├── console/
│   │   └── form.py           # Console JSON-Schema form
│   └── textual/
│       └── form.py           # Textual TUI JSON-Schema form dialog
├── tests/                    # Test suite
├── requirements.txt
├── requirements.lock.txt
└── Makefile
```

## License

Distributed under the [Apache License 2.0](LICENSE).
