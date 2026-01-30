# User Guide

## 1. Installation

### Prerequisites

- **Python >= 3.12**
- **make** (GNU Make or compatible)

### Steps

```bash
git clone https://github.com/RubenCiveira/asistente.git
cd asistente

# Build the project (creates virtualenv and installs dependencies)
make build
```

---

## 2. Launching the Application

Start the TUI with:

```bash
PYTHONPATH=src python src/window.py
```

The application opens a full-screen terminal interface with a tabbed layout.
On first launch a default session is created automatically. If a previous
configuration exists at `~/.config/asistente/asistente.json`, all saved
sessions are restored and the last active tab is re-selected.

---

## 3. Keyboard Shortcuts

| Shortcut  | Action                        |
|-----------|-------------------------------|
| `Ctrl+W`  | Open the workspace selector   |
| `Ctrl+Y`  | Open the project selector     |
| `Ctrl+N`  | Create a new session tab      |
| `Ctrl+D`  | Close the current session tab |
| `Ctrl+Q`  | Quit the application          |

---

## 4. Managing Workspaces

Press **Ctrl+W** to open the workspace selection flow.

1. A form dialog appears listing your **recent workspaces** (up to 10).
2. Select an existing workspace from the list, **or** choose
   "Otro directorio..." to browse for a new one.
3. If you choose the browse option, a **path dialog** opens so you can
   navigate the filesystem and pick (or create) a directory to use as the
   workspace root.
4. The workspace manifest (`workspace.json`) is loaded from the chosen
   directory. If none exists, a new one is initialised automatically.
5. After the workspace is set, the application **automatically chains** into
   the project selection flow (see next section).

The active workspace path is persisted in the application configuration so it
is remembered across restarts.

---

## 5. Managing Projects

Press **Ctrl+Y** to open the project selection flow directly, or reach it
automatically after selecting a workspace.

1. If the current workspace has **known projects**, a form dialog lists them.
2. Select an existing project, **or** choose "Otro directorio..." to add a
   new one.
3. If you choose to add a new project:
   - A **path dialog** opens so you can browse to a project directory.
   - If the directory does not exist, a **confirmation dialog** asks whether
     to create it.
4. The project manifest (`.conf/assistants/project.json` inside the project
   root) is loaded or created.
5. The workspace's project list and active project are updated and saved.

---

## 6. Sessions and Tabs

Each session represents an independent chat context with its own workspace and
project bindings.

### Creating a session

Press **Ctrl+N**. A new tab appears on the right of the tab bar and is
immediately activated. The new session starts with no workspace or project --
use **Ctrl+W** to configure it.

### Switching between sessions

Click on a tab header or use the built-in Textual tab navigation to move
between sessions. The header bar updates to show the active session's workspace
and project.

### Closing a session

Press **Ctrl+D**. A confirmation dialog appears. If confirmed, the current tab
and its associated session are removed. The application switches to the nearest
remaining tab. If this was the last session, a fresh session is created
automatically, inheriting the same workspace and project.

### Persistence

All sessions (including their IDs, workspace paths, and project paths) are
serialised to `~/.config/asistente/asistente.json` whenever the session list
changes. On the next launch the sessions are restored exactly as they were.

---

## 7. Form Dialogs

Several flows present a **wizard-style form dialog** powered by JSON Schema
(Draft 2020-12).

### How it works

- The dialog renders one field at a time.
- Use **Next** to advance to the following field and **Back** (or Escape) to
  return to the previous one.
- Each field is validated incrementally as you navigate forward. Invalid input
  prevents progression until corrected.
- When you complete the last field and press **Ok**, the form returns the
  collected values.
- Press **Escape** on the first field to cancel the dialog entirely.

### Supported field types

| JSON Schema type | Rendered as          |
|------------------|----------------------|
| `string`         | Text input           |
| `integer`        | Numeric input        |
| `number`         | Numeric input        |
| `boolean`        | Checkbox             |
| `enum`           | Radio selection      |
| `oneOf`          | Radio selection      |
| `array`          | Multi-select or list |

---

## 8. Path Dialog

The path dialog is used whenever you need to select a file or directory on the
filesystem.

### Features

- **Autocomplete**: As you type a path, suggestions are shown for matching
  files and directories under the root.
- **Browsing**: Navigate the filesystem interactively by typing path segments.
- **Constraints**: Depending on the context the dialog may restrict selection
  to directories only, files only, or any entry. It may also enforce that the
  selected path already exists.
- **Root restriction**: Browsing is constrained to a specific root directory
  (typically `$HOME`).
- **Name filter**: An optional regex pattern can limit which entries are shown.

Press **Enter** or the **OK** button to confirm your selection. Press
**Escape** or the **Cancel** button to dismiss without selecting.

---

## 9. Configuration Files

The application uses three JSON files for persistence. All are human-readable
and can be edited manually if needed.

### Application configuration

| Field                  | Description                                         |
|------------------------|-----------------------------------------------------|
| **Path**               | `~/.config/asistente/asistente.json`                |
| `active_workspace`     | Path of the last selected workspace                 |
| `recent_workspaces`    | List of up to 10 recently used workspace paths      |
| `sessions`             | Array of `{id, workspace, project}` objects          |
| `active_session_index` | Index of the last active session                     |

### Workspace manifest

| Field              | Description                                     |
|--------------------|-------------------------------------------------|
| **Path**           | `<workspace_root>/workspace.json`               |
| `name`             | Workspace display name (defaults to dir name)   |
| `created_at`       | ISO-8601 creation timestamp                     |
| `projects`         | List of registered project directory paths      |
| `active_project`   | Path to the currently active project            |

### Project manifest

| Field          | Description                                         |
|----------------|-----------------------------------------------------|
| **Path**       | `<project_root>/.conf/assistants/project.json`      |
| `id`           | Unique project UUID                                 |
| `name`         | Project display name (defaults to dir name)         |
| `description`  | Free-text project description                       |
| `status`       | Lifecycle status (e.g. `"active"`)                  |
| `metadata`     | Arbitrary key/value pairs                           |
