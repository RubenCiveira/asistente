# API Reference

Module-by-module reference for the active codebase (everything outside
`src/old/`).

---

## `app.context.session`

Lightweight session container binding a UUID to an optional workspace and
project.

### `_new_session_id() -> str`

Generate a new UUID-4 string for use as a session identifier.

### `class Session`

In-memory session record tying a unique identifier to an active workspace and
project.

| Attribute   | Type                  | Default                |
|-------------|-----------------------|------------------------|
| `id`        | `str`                 | UUID-4 via factory     |
| `workspace` | `Optional[Workspace]` | `None`                 |
| `project`   | `Optional[Project]`   | `None`                 |

---

## `app.context.project`

Project metadata backed by a JSON file at `.conf/assistants/project.json`.

### `class Project`

A project with identity and metadata persisted to disk.

| Attribute     | Type             | Description                          |
|---------------|------------------|--------------------------------------|
| `id`          | `str`            | Unique identifier (UUID-4)           |
| `name`        | `str`            | Human-readable name                  |
| `description` | `str`            | Free-text description                |
| `status`      | `str`            | Lifecycle status (e.g. `"active"`)   |
| `root_dir`    | `Path`           | Absolute path to project root        |
| `metadata`    | `Dict[str, Any]` | Arbitrary key/value pairs            |

**Class constant:**

- `CONFIG_RELATIVE_PATH = Path(".conf/assistants/project.json")`

#### `load_or_create(project_dir: Path) -> Project` *(classmethod)*

Load an existing project from *project_dir* or create a new one. The
directory is created if it does not exist.

#### `save() -> None`

Persist the project configuration to disk.

---

## `app.context.workspace`

Workspace grouping backed by `workspace.json` inside the workspace root.

### `class Workspace`

A named directory that groups related projects.

| Attribute        | Type              | Description                       |
|------------------|-------------------|-----------------------------------|
| `root_dir`       | `Path`            | Absolute path to workspace root   |
| `name`           | `str`             | Human-readable name               |
| `created_at`     | `str`             | ISO-8601 creation timestamp       |
| `projects`       | `List[Path]`      | Registered project paths          |
| `active_project` | `Optional[Path]`  | Currently selected project path   |

#### `file -> Path` *(property)*

Return the path to `workspace.json` inside the workspace root.

#### `load_or_create(root_dir: Path) -> Workspace` *(classmethod)*

Load an existing workspace from *root_dir* or create a new one. The
directory is created when it does not exist.

#### `add_project(project_dir: Path) -> None`

Register a project directory with this workspace. Duplicates are ignored.
The workspace manifest is saved after every call.

#### `set_active_project(project_dir: Path) -> None`

Mark *project_dir* as the active project and register it.

#### `save() -> None`

Persist the workspace manifest to `workspace.json`.

---

## `app.config`

Application-level configuration persisted as JSON in the user config directory.

### `default_config_path() -> Path`

Return the conventional path to the application config file
(`~/.config/asistente/asistente.json`).

### `default_workspaces_dir() -> Path`

Return the default directory for workspace storage
(`~/.config/asistente/workspaces`).

### `class AppConfig`

Application configuration backed by a JSON file.

| Attribute              | Type                            | Default   |
|------------------------|---------------------------------|-----------|
| `config_path`          | `Path`                          | required  |
| `active_workspace`     | `Optional[Path]`                | `None`    |
| `recent_workspaces`    | `List[Path]`                    | `[]`      |
| `sessions`             | `List[Dict[str, Optional[str]]]`| `[]`      |
| `active_session_index` | `int`                           | `0`       |

#### `load(path: Optional[Path] = None) -> AppConfig` *(classmethod)*

Load the configuration from a JSON file. If the file does not exist an
`AppConfig` with default values is returned.

#### `save() -> None`

Persist the current configuration to disk as pretty-printed JSON. Parent
directories are created automatically.

#### `set_active_workspace(path: Path) -> None`

Set *path* as the active workspace and prepend it to the recent list.
Duplicates are removed and the list is capped at 10 entries.

---

## `app.ui.textual.confirm`

Simple yes/no confirmation modal for Textual applications.

### `class Confirm(ModalScreen[bool])`

Modal confirmation dialog.

| Parameter     | Type  | Default      |
|---------------|-------|--------------|
| `title`       | `str` | `"Confirm"`  |
| `subtitle`    | `str` | `""`         |
| `ok_text`     | `str` | `"OK"`       |
| `cancel_text` | `str` | `"Cancel"`   |

**Bindings:** `Escape` -> cancel

#### `compose() -> ComposeResult`

Build the dialog widget tree.

#### `on_button_pressed(event: Button.Pressed) -> None`

Dismiss with `True` for OK, `False` for Cancel.

#### `action_cancel() -> None`

Handle the Escape key by dismissing with `False`.

---

## `app.ui.textual.form`

Textual modal form dialog driven by JSON Schema (Draft 2020-12).

### `class FormDialog(ModalScreen[Optional[Dict[str, Any]]])`

Modal dialog that renders a JSON-Schema-driven form with incremental
validation.

| Parameter        | Type                       | Description                    |
|------------------|----------------------------|--------------------------------|
| `schema`         | `Dict[str, Any]`           | JSON Schema object definition  |
| `initial_values` | `Optional[Dict[str, Any]]` | Pre-populate fields            |

**Returns:** `dict` on success, `None` on cancel.

**Bindings:** `Escape` -> back or cancel

#### Key methods

- `compose() -> ComposeResult` -- Build the static widget tree.
- `on_mount()` -- Render the first field.
- `action_back_or_cancel()` -- Go back one field or cancel.
- `_render_field()` -- Mount the widget for the current field.
- `_submit_current()` -- Validate, store and advance.
- `_read_widget_value()` -- Extract value from the active widget.
- `_validate_field_incremental(field_name, candidate_value) -> List[str]`
- `_cast_value(raw, field_type)` -- Convert string to typed value.
- `_add_array_item()` -- Add an item to the free-text array list.
- `_remove_array_item(lv, idx)` -- Remove an item by index.

---

## `app.ui.textual.path_dialog`

File and directory browser modal with autocomplete suggestions.

### `class PathDialog(ModalScreen[Optional[Path]])`

Modal path-selection dialog with filesystem autocomplete.

| Parameter             | Type              | Default           |
|-----------------------|-------------------|-------------------|
| `root_dir`            | `Path`            | required          |
| `must_exist`          | `bool`            | `True`            |
| `warn_if_exists`      | `bool`            | `False`           |
| `select`              | `str`             | `"any"`           |
| `initial_path`        | `Path \| None`    | `None`            |
| `name_filter`         | `str \| None`     | `None`            |
| `relative_check_path` | `Path \| None`    | `None`            |
| `title`               | `str`             | `"Select path"`   |
| `sub_title`           | `str`             | `""`              |
| `max_suggestions`     | `int`             | `30`              |

**Returns:** `Path` on success, `None` on cancel.

**Bindings:** `Escape` -> cancel

#### Key methods

- `compose()` -- Build the dialog widget tree.
- `on_mount()` -- Focus the path input.
- `action_cancel()` -- Dismiss with `None`.
- `_candidates(state) -> List[DropdownItem]` -- Autocomplete callback.
- `_try_accept()` -- Validate and dismiss.
- `_validate(raw) -> Optional[Path]` -- Run all validation constraints.
- `_to_absolute(relative) -> Path` -- Convert user input to absolute path.

---

## `app.ui.console.form`

Console (prompt_toolkit) form renderer driven by JSON Schema.

### `class _EscapePressed(Exception)`

Sentinel exception raised when the user presses Escape during input.

### `class ConsoleFormRenderer`

Interactive terminal form renderer backed by JSON Schema.

| Attribute     | Type                    | Description               |
|---------------|-------------------------|---------------------------|
| `schema`      | `Dict[str, Any] \| None`| The active schema         |
| `field_order` | `List[str]`             | Ordered property names    |

#### `ask_form(json_schema: Dict[str, Any]) -> Dict[str, Any] | None`

Prompt the user for every field in *json_schema* and return the result.
Returns `None` if the user cancels.

#### `_validate_field_incremental(*, field_name, candidate_value, partial_data) -> List[str]`

Validate a single field in the context of previously filled fields.

#### `_ask_field(name, spec, required, partial_data) -> Any`

Prompt for a single field, dispatching to the appropriate input handler.

#### `_ask_scalar(label, field_type, default, required) -> Any`

Prompt for a simple scalar value.

#### `_ask_enum(label, enum, default, required, field_type) -> Any`

Prompt for a value from a fixed set of allowed values.

#### `_ask_one_of(label, options, default, required) -> Any`

Prompt for a selection from a `oneOf` list of titled constants.

#### `_ask_array(label, spec, required, field_name, partial_data) -> list`

Prompt for an array value (multi-select or free-text items).

#### `_cast_value(raw: str, field_type: str) -> Any`

Convert a raw string to the Python type indicated by *field_type*.

#### `_validate_array_item(item_value, item_schema) -> list[str]`

Validate a single array element against the `items` sub-schema.

#### `_validate_array_partial(field_name, values, partial_data) -> list[str]`

Validate the full array in the incremental context.

---

## `app.ui.textual.action.select_project`

TUI action for selecting or creating a project within the active workspace.

### `class SelectProject`

Action that guides the user through picking or creating a project.

| Parameter | Type  | Description               |
|-----------|-------|---------------------------|
| `window`  | `Any` | The main application instance |

#### `run() -> None` *(async)*

Execute the full project-selection flow. Shows an error if no workspace is
active.

#### `select_project(ws) -> Optional[Project]` *(async)*

Show a form with existing projects or fall through to `new_project()`.

#### `new_project() -> Optional[Project]` *(async)*

Open a `PathDialog` for the user to pick a new project directory. Shows a
confirmation dialog if the directory does not exist.

---

## `app.ui.textual.action.select_workspace`

TUI action for selecting or creating a workspace, followed by project
selection.

### `class SelectWorkspace`

Action that guides the user through picking or creating a workspace.

| Parameter        | Type            | Description                  |
|------------------|-----------------|------------------------------|
| `window`         | `Any`           | The main application instance|
| `select_project` | `SelectProject` | Chained project action       |

#### `run() -> None` *(async)*

Execute the full workspace-then-project selection flow.

#### `select_workspace() -> Optional[Workspace]` *(async)*

Show a form listing recent workspaces or create a new one.

#### `new_worksapce() -> Optional[Workspace]` *(async)*

Open a `PathDialog` for the user to pick a new workspace directory.

---

## `window`

Textual TUI entry point providing a tabbed multi-session chat interface.

### `class MainApp(App)`

Tabbed multi-session Textual application.

| Attribute        | Type              | Description                     |
|------------------|-------------------|---------------------------------|
| `config`         | `AppConfig`       | Application configuration       |
| `sessions`       | `list[Session]`   | All open sessions               |
| `active_session` | `Session`         | Currently active session        |

**Bindings:**

| Key      | Action               |
|----------|----------------------|
| `Ctrl+W` | `select_workspace`   |
| `Ctrl+Y` | `select_project`     |
| `Ctrl+N` | `new_session`        |
| `Ctrl+D` | `close_session`      |
| `Ctrl+Q` | `quit`               |

#### Key methods

- `get_active_workspace()` -- Return the workspace of the active session.
- `get_active_project()` -- Return the project of the active session.
- `select_workspace(ws)` -- Set workspace, clear project, persist.
- `select_project(prj)` -- Set project, persist.
- `echo(result)` -- Append a Markdown widget to the active chat.
- `compose() -> ComposeResult` -- Build the widget tree.
- `on_mount()` -- Restore workspace/project references from config.
- `action_new_session()` -- Create a new empty session tab.
- `action_close_session()` -- Close the active session after confirmation.
- `on_input_submitted(event)` -- Append user message to active chat.
