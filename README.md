# Asistente

Tabbed TUI assistant for managing workspaces, projects and interactive
sessions.  Built on [Textual](https://textual.textualize.io/) with
JSON-Schema-driven forms and filesystem browsing with autocomplete.

> **Note:** Legacy multi-agent LangChain code lives under `src/old/` and is
> not part of the active codebase.

## Features

- **Multi-session tabs** — open several independent sessions, each bound to
  its own workspace and project.  Sessions are persisted across restarts.
- **Workspace / project model** — organise work into workspaces (directories
  that group projects) and projects (directories with their own config).
- **Trigger-based autocomplete** — chat input with multi-trigger completion
  (`/` commands, `@` context references, `:` power-user commands, `#`
  semantic entities) powered by pluggable providers.
- **JSON-Schema-driven forms** — both the console (`prompt_toolkit`) and the
  TUI (Textual) renderers build forms dynamically from JSON Schema (Draft
  2020-12) with incremental cross-field validation.
- **Path dialog with autocomplete** — browse the filesystem inside a modal
  with type-ahead suggestions, filtering and validation constraints.
- **Confirmation dialogs** — reusable yes/no modal for destructive actions.

## Requirements

- Python >= 3.12
- A terminal that supports Textual (most modern terminals).

## Quick start

```bash
# Clone
git clone https://github.com/RubenCiveira/asistente.git
cd asistente

# Install
make build

# Run the TUI
PYTHONPATH=src python src/window.py
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
├── src/
│   ├── window.py                          # Textual TUI entry point
│   └── app/
│       ├── config.py                      # Application config (JSON persistence)
│       ├── context/
│       │   ├── keywords.py               # Trigger/keyword utilities for autocomplete
│       │   ├── project.py                 # Project metadata dataclass
│       │   ├── session.py                 # Session (UUID, workspace, project refs)
│       │   └── workspace.py               # Workspace manifest dataclass
│       └── ui/
│           ├── console/
│           │   └── form.py                # Console JSON-Schema form renderer
│           └── textual/
│               ├── widgets/
│               │   ├── chat_input.py      # Chat input with trigger-based autocomplete
│               │   ├── confirm.py         # Yes/no modal dialog
│               │   ├── form.py            # Wizard-style JSON-Schema form dialog
│               │   ├── path_dialog.py     # File/directory browser with autocomplete
│               │   └── token_aware_auto_complete.py  # Token-aware autocomplete overlay
│               ├── action/
│               │   ├── select_project.py  # Action: pick or create a project
│               │   └── select_workspace.py # Action: pick or create a workspace
│               └── completion_provider/
│                   ├── slash_provider.py   # "/" command completions
│                   ├── at_provider.py      # "@" context reference completions
│                   ├── colon_provider.py   # ":" power-user command completions
│                   └── hash_provider.py    # "#" semantic entity completions
├── test/                                   # pytest test suite
├── docs/                                   # Technical and user documentation
├── Makefile
├── requirements.txt
├── requirements.lock.txt
├── CONTRIBUTING.md
└── LICENSE
```

## License

Distributed under the [Apache License 2.0](LICENSE).
