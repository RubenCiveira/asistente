# Architecture Overview

## 1. Introduction

**Asistente** is a Python TUI (Text User Interface) application built on
[Textual](https://textual.textualize.io/). It provides a tabbed, multi-session
chat interface where each session is scoped to a **workspace** and an optional
**project**. The application persists its state entirely through JSON files -- no
database is required.

The codebase follows a layered architecture that separates presentation,
coordination logic (actions), domain models, and persistence concerns.

---

## 2. Layer Diagram

```mermaid
graph TD
    subgraph Presentation
        MainApp["MainApp (window.py)"]
        Confirm["Confirm (confirm.py)"]
        FormDialog["FormDialog (form.py)"]
        PathDialog["PathDialog (path_dialog.py)"]
        ConsoleFormRenderer["ConsoleFormRenderer (console/form.py)"]
    end

    subgraph Actions
        SelectWorkspace["SelectWorkspace"]
        SelectProject["SelectProject"]
    end

    subgraph Domain
        AppConfig["AppConfig"]
        Session["Session"]
        Workspace["Workspace"]
        Project["Project"]
    end

    subgraph Persistence
        AppJSON["~/.config/asistente/asistente.json"]
        WorkspaceJSON["&lt;workspace&gt;/workspace.json"]
        ProjectJSON["&lt;project&gt;/.conf/assistants/project.json"]
    end

    MainApp --> SelectWorkspace
    MainApp --> SelectProject
    MainApp --> Confirm
    MainApp --> FormDialog
    MainApp --> PathDialog

    SelectWorkspace --> FormDialog
    SelectWorkspace --> PathDialog
    SelectWorkspace --> SelectProject
    SelectProject --> FormDialog
    SelectProject --> PathDialog
    SelectProject --> Confirm

    SelectWorkspace --> Workspace
    SelectProject --> Project
    MainApp --> Session
    MainApp --> AppConfig

    AppConfig --> AppJSON
    Workspace --> WorkspaceJSON
    Project --> ProjectJSON
```

---

## 3. Class Diagram

```mermaid
classDiagram
    class MainApp {
        +sessions: list~Session~
        +active_session: Session
        +config: AppConfig
        +compose() ComposeResult
        +action_select_workspace()
        +action_select_project()
        +action_new_session()
        +action_close_session()
        +action_quit()
        +select_workspace(ws)
        +select_project(prj)
        +echo(result)
    }

    class AppConfig {
        +config_path: Path
        +active_workspace: Optional~Path~
        +recent_workspaces: list~Path~
        +sessions: list~dict~
        +active_session_index: int
        +load(path) AppConfig
        +save()
        +set_active_workspace(path)
    }

    class Session {
        +id: str
        +workspace: Optional~Workspace~
        +project: Optional~Project~
    }

    class Workspace {
        +root_dir: Path
        +name: str
        +created_at: str
        +projects: list~Path~
        +active_project: Optional~Path~
        +file: Path
        +load_or_create(root_dir) Workspace
        +add_project(path)
        +set_active_project(path)
        +save()
    }

    class Project {
        +id: str
        +name: str
        +description: str
        +status: str
        +root_dir: Path
        +metadata: dict
        +load_or_create(root_dir) Project
        +save()
    }

    class Confirm {
        +title: str
        +subtitle: str
        +ok_text: str
        +cancel_text: str
        +compose()
        +action_cancel()
    }

    class FormDialog {
        +schema: dict
        +properties: dict
        +required: set
        +field_order: list
        +data: dict
        +compose() ComposeResult
    }

    class PathDialog {
        +root_dir: Path
        +must_exist: bool
        +select: str
        +initial_path: Optional~Path~
        +name_filter: Optional~Pattern~
        +compose()
        +action_cancel()
    }

    class ConsoleFormRenderer {
        +schema: dict
        +field_order: list
        +ask_form(json_schema) dict
    }

    class SelectWorkspace {
        +window: MainApp
        +select_project: SelectProject
        +run()
        +select_workspace() Workspace
        +new_worksapce() Workspace
    }

    class SelectProject {
        +window: MainApp
        +run()
        +select_project(ws) Project
        +new_project() Project
    }

    MainApp "1" --> "1" AppConfig : reads/writes
    MainApp "1" --> "*" Session : manages
    Session "1" --> "0..1" Workspace
    Session "1" --> "0..1" Project
    Workspace "1" --> "*" Project : references
    MainApp ..> SelectWorkspace : invokes
    MainApp ..> SelectProject : invokes
    SelectWorkspace ..> FormDialog : opens
    SelectWorkspace ..> PathDialog : opens
    SelectWorkspace ..> SelectProject : chains to
    SelectProject ..> FormDialog : opens
    SelectProject ..> PathDialog : opens
    SelectProject ..> Confirm : opens
    Confirm --|> ModalScreen~bool~
    FormDialog --|> ModalScreen~dict~
    PathDialog --|> ModalScreen~Path~
```

---

## 4. Sequence Diagram -- Workspace Selection Flow

```mermaid
sequenceDiagram
    actor User
    participant MainApp
    participant SelectWorkspace
    participant FormDialog
    participant PathDialog
    participant Workspace
    participant SelectProject

    User->>MainApp: Ctrl+W
    MainApp->>SelectWorkspace: run()
    SelectWorkspace->>FormDialog: show recent workspaces
    FormDialog-->>SelectWorkspace: selected key or "__new__"

    alt User selects "__new__"
        SelectWorkspace->>PathDialog: browse for directory
        PathDialog-->>SelectWorkspace: chosen Path
    end

    SelectWorkspace->>Workspace: load_or_create(path)
    Workspace-->>SelectWorkspace: Workspace instance
    SelectWorkspace->>MainApp: select_workspace(ws)
    SelectWorkspace->>SelectProject: run()
    SelectProject->>FormDialog: show known projects
    FormDialog-->>SelectProject: selected project or "__new__"

    alt User selects "__new__"
        SelectProject->>PathDialog: browse for project dir
        PathDialog-->>SelectProject: chosen Path
    end

    SelectProject-->>MainApp: select_project(prj)
    MainApp->>AppConfig: save()
```

---

## 5. Sequence Diagram -- Session Lifecycle

```mermaid
sequenceDiagram
    actor User
    participant MainApp
    participant AppConfig
    participant Session

    Note over User,Session: Creating a new session (Ctrl+N)
    User->>MainApp: Ctrl+N
    MainApp->>Session: Session() with new UUID
    MainApp->>MainApp: add TabPane + VerticalScroll
    MainApp->>MainApp: activate new tab
    MainApp->>AppConfig: save()

    Note over User,Session: Closing a session (Ctrl+D)
    User->>MainApp: Ctrl+D
    MainApp->>MainApp: push Confirm dialog
    MainApp-->>MainApp: confirmed = True
    MainApp->>MainApp: remove TabPane
    MainApp->>MainApp: remove Session from list
    MainApp->>MainApp: activate adjacent tab
    MainApp->>AppConfig: save()

    Note over User,Session: Restoring sessions on startup
    MainApp->>AppConfig: load()
    AppConfig-->>MainApp: sessions list + active_session_index
    loop for each saved session
        MainApp->>Session: reconstruct from dict
        MainApp->>MainApp: create TabPane + VerticalScroll
    end
    MainApp->>MainApp: activate tab at active_session_index
```

---

## 6. Persistence Model

The application stores all of its state in three JSON files. No external
database is required.

### 6.1 Application Configuration

| Property      | Value                                      |
|---------------|--------------------------------------------|
| **Location**  | `~/.config/asistente/asistente.json`       |
| **Managed by**| `AppConfig`                                |
| **Contains**  | Active workspace path, list of up to 10 recent workspaces, serialised session list, active session index |

### 6.2 Workspace Manifest

| Property      | Value                                      |
|---------------|--------------------------------------------|
| **Location**  | `<workspace_root>/workspace.json`          |
| **Managed by**| `Workspace`                                |
| **Contains**  | Workspace name, creation timestamp, list of project paths, currently active project path |

### 6.3 Project Manifest

| Property      | Value                                      |
|---------------|--------------------------------------------|
| **Location**  | `<project_root>/.conf/assistants/project.json` |
| **Managed by**| `Project`                                  |
| **Contains**  | Project UUID, name, description, status, root directory, arbitrary metadata dict |

---

## 7. Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Textual for the TUI** | Provides a modern, CSS-styled widget toolkit with async support and built-in modal screens, which maps naturally to the tabbed chat interface. |
| **Dataclasses for domain models** | Keeps the domain layer lightweight and free of framework dependencies. Serialisation to/from JSON is straightforward. |
| **JSON file persistence** | Eliminates external dependencies (no SQLite, no ORM). Each concern writes its own file in a predictable location, making manual inspection and backup trivial. |
| **UUID-4 identifiers** | Guarantees globally unique session and project IDs without coordination. |
| **ModalScreen pattern** | Textual's `ModalScreen` with a typed return value (`ModalScreen[bool]`, `ModalScreen[dict]`, `ModalScreen[Path]`) gives a clean request/response contract for dialogs. |
| **JSON Schema for forms** | A single schema definition drives both the Textual `FormDialog` and the fallback `ConsoleFormRenderer`, ensuring consistent validation across UIs. |
| **Action classes** | Encapsulating multi-step flows (workspace selection, project selection) into dedicated action classes keeps `MainApp` thin and each flow independently testable. |
| **Workspace to Project chaining** | Selecting a workspace automatically chains into project selection, reducing the number of manual steps for the user. |
| **Recent workspaces cap (10)** | Prevents the list from growing unbounded while still providing quick access to frequently used workspaces. |
| **Separation of console and textual renderers** | Allows the form logic to be reused in non-TUI contexts (scripts, CI pipelines) via `ConsoleFormRenderer` backed by `prompt_toolkit`. |
