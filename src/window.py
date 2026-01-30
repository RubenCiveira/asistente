"""Textual TUI entry point providing a tabbed multi-session chat interface.

Each tab corresponds to a :class:`~app.context.session.Session` that binds a
workspace and a project.  The application persists open sessions to disk so
that they are restored on the next launch.

Keyboard shortcuts:
    Ctrl+W  Select workspace
    Ctrl+Y  Select project
    Ctrl+N  Open a new session tab
    Ctrl+D  Close the active session tab
    Ctrl+Q  Quit
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Markdown, TabbedContent, TabPane
from textual.containers import Vertical, VerticalScroll
from rich.text import Text

from app.config import AppConfig
from app.context.workspace import Workspace
from app.context.project import Project
from app.context.session import Session
from app.context.keywords import Keywords

from app.ui.textual.confirm import Confirm
from app.ui.textual.chat_input import ChatInput
from app.ui.textual.action.select_project import SelectProject
from app.ui.textual.action.select_workspace import SelectWorkspace
from app.ui.textual.completion_provider.slash_provider import SlashCommandProvider
from app.ui.textual.completion_provider.at_provider import ContextProvider
from app.ui.textual.completion_provider.colon_provider import PowerCommandProvider
from app.ui.textual.completion_provider.hash_provider import SemanticProvider

class MainApp(App):
    """Tabbed multi-session Textual application.

    Manages a list of :class:`~app.context.session.Session` objects, each
    rendered as a tab with its own chat scroll area.  Workspace and project
    selection, session creation/closing and header updates are handled
    through keyboard bindings and action helpers.
    """

    CSS = """
    #tabs {
        height: 1fr;
    }

    .session-chat {
        height: 1fr;
        border: round $primary;
        padding: 1 2;
        overflow-y: auto;
    }

    #prompt {
        border: round $accent;
    }
    """

    BINDINGS = [
        ("ctrl+w", "select_workspace", "Workspace"),
        ("ctrl+y", "select_project", "Project"),
        ("ctrl+n", "new_session", "New tab"),
        ("ctrl+d", "close_session", "Close tab"),
        ("ctrl+k", "clear_text", "Clear text"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialise the app, restoring sessions from the persisted config."""
        super().__init__()
        self.config = AppConfig.load()

        saved = self.config.sessions
        if saved:
            self.sessions = [
                Session(id=s["id"]) if s.get("id") else Session()
                for s in saved
            ]
        else:
            self.sessions = [Session()]

        idx = max(0, min(self.config.active_session_index, len(self.sessions) - 1))
        self.active_session = self.sessions[idx]

        self._select_project_action = SelectProject(self)
        self._select_workspace_action = SelectWorkspace(self, self._select_project_action)

    def get_active_workspace(self):
        """Return the workspace of the active session (may be ``None``)."""
        return self.active_session.workspace

    def get_active_project(self):
        """Return the project of the active session (may be ``None``)."""
        return self.active_session.project

    def select_workspace(self, ws) -> None:
        """Set *ws* as the active workspace, clear the project and persist."""
        self.active_session.workspace = ws
        self.active_session.project = None
        self.config.set_active_workspace(ws.root_dir)
        self._update_tab_label(self.active_session)
        self._save_sessions()
        self._refresh_header()

    def select_project(self, prj) -> None:
        """Set *prj* as the active project and persist."""
        self.active_session.workspace.set_active_project(prj.root_dir)
        self.active_session.project = prj
        self._update_tab_label(self.active_session)
        self._save_sessions()
        self._refresh_header()

    def _save_sessions(self) -> None:
        """Serialise all sessions to the config and write to disk."""
        self.config.sessions = [
            {
                "id": s.id,
                "workspace": str(s.workspace.root_dir) if s.workspace else None,
                "project": str(s.project.root_dir) if s.project else None,
            }
            for s in self.sessions
        ]
        self.config.active_session_index = self.sessions.index(self.active_session)
        self.config.save()

    def echo(self, result: Markdown | string | None) -> None:
        """Append a :class:`Markdown` widget to the active chat and scroll down."""
        if result is None:
            return
        chat = self._active_chat()
        if isinstance(result, Markdown):
            widget = result
        else:
            # si el chat espera un widget, lo conviertes a Markdown (o a Label/Static)
            widget = Markdown(str(result))
        chat.mount(widget)
        chat.scroll_end(animate=False)

    def _log(self, text: str) -> None:
        """Convenience wrapper: mount a Markdown widget with *text*."""
        chat = self._active_chat()
        chat.mount(Markdown(text))
        chat.scroll_end(animate=False)

    def _active_chat(self) -> VerticalScroll:
        """Return the chat scroll container for the active session."""
        return self.query_one(f"#chat-{self.active_session.id}", VerticalScroll)

    def on_mount(self) -> None:
        """Restore workspace/project references for every session from config."""
        saved = self.config.sessions
        for i, session in enumerate(self.sessions):
            if i < len(saved):
                ws_path = saved[i].get("workspace")
                prj_path = saved[i].get("project")
                if ws_path:
                    p = Path(ws_path)
                    if p.exists():
                        try:
                            ws = Workspace.load_or_create(p)
                            session.workspace = ws
                            if prj_path:
                                pp = Path(prj_path)
                                if pp.exists():
                                    prj = Project.load_or_create(pp)
                                    session.project = prj
                        except Exception:
                            pass

        # Compatibilidad: si no habia sesiones guardadas, cargar workspace por defecto
        if not saved and self.config.active_workspace and self.config.active_workspace.exists():
            try:
                ws = Workspace.load_or_create(self.config.active_workspace)
                self.active_session.workspace = ws
                if ws.active_project and ws.active_project.exists():
                    prj = Project.load_or_create(ws.active_project)
                    self.active_session.project = prj
            except Exception:
                pass

        for session in self.sessions:
            self._update_tab_label(session)
        self._refresh_header()

    def compose(self) -> ComposeResult:
        """Build the widget tree: header, tabbed chat areas, input and footer."""
        resolvers = {
                "/": SlashCommandProvider(),
                "@": ContextProvider(),
                ":": PowerCommandProvider(),
                "#": SemanticProvider(),
            }
        chat = ChatInput(
            keywords=Keywords( sorted(resolvers.keys(), key=len, reverse=True) ),
            triggers=resolvers,
            id="chat_input",
        )
        yield Header()
        with Vertical():
            with TabbedContent(id="tabs"):
                for session in self.sessions:
                    with TabPane(self._tab_label(session), id=f"tab-{session.id}"):
                        yield VerticalScroll(id=f"chat-{session.id}", classes="session-chat")
            # yield Input(placeholder="Escribe aqui... (Enter para enviar)", id="prompt")
            yield chat
            yield Footer()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Update :attr:`active_session` and the header when the user switches tabs."""
        pane_id = event.pane.id or ""
        sid = pane_id.removeprefix("tab-")
        for s in self.sessions:
            if s.id == sid:
                self.active_session = s
                break
        self._refresh_header()

    def _tab_label(self, session: Session) -> str:
        """Derive a human-readable tab label: project > workspace > default."""
        if session.project:
            return session.project.name
        if session.workspace:
            return session.workspace.name
        return "Nueva sesion"

    def _update_tab_label(self, session: Session) -> None:
        """Refresh the displayed label of the tab for *session*."""
        tabs = self.query_one("#tabs", TabbedContent)
        tab = tabs.get_tab(f"tab-{session.id}")
        tab.label = self._tab_label(session)

    def action_clear_text(self) -> None:
        chat = self._active_chat()
        chat.remove_children()
        chat.refresh(layout=True)
        chat.scroll_end(animate=False)

    def action_select_project(self) -> None:
        """Keybinding action: launch the project-selection flow."""
        self.run_worker(self._select_project_action.run())

    def action_select_workspace(self) -> None:
        """Keybinding action: launch the workspace-selection flow."""
        self.run_worker(self._select_workspace_action.run())

    def action_new_session(self) -> None:
        """Keybinding action: create a new empty session tab."""
        self.run_worker(self._new_session())

    async def _new_session(self) -> None:
        """Create a new session, add a tab for it and activate it."""
        session = Session()
        self.sessions.append(session)

        tabs = self.query_one("#tabs", TabbedContent)
        pane = TabPane(self._tab_label(session), id=f"tab-{session.id}")
        await tabs.add_pane(pane)

        pane_widget = self.query_one(f"#tab-{session.id}", TabPane)
        await pane_widget.mount(VerticalScroll(id=f"chat-{session.id}", classes="session-chat"))

        tabs.active = f"tab-{session.id}"
        self.active_session = session
        self._save_sessions()
        self._refresh_header()

    def action_close_session(self) -> None:
        """Keybinding action: close the active session after confirmation."""
        self.run_worker(self._close_session())

    async def _close_session(self) -> None:
        """Ask for confirmation and close the active session.

        When the last remaining session is closed a replacement session
        inheriting the same workspace and project is created automatically.
        """
        confirmed = await self.push_screen_wait(Confirm(
            title="Cerrar sesion",
            subtitle="Se cerrara la sesion actual y su tab.",
            ok_text="Cerrar",
            cancel_text="Cancelar",
        ))
        if not confirmed:
            return

        closing = self.active_session
        was_last = len(self.sessions) == 1

        if was_last:
            new_session = Session()
            new_session.workspace = closing.workspace
            new_session.project = closing.project
            self.sessions.append(new_session)

            tabs = self.query_one("#tabs", TabbedContent)
            pane = TabPane(self._tab_label(new_session), id=f"tab-{new_session.id}")
            await tabs.add_pane(pane)
            pane_widget = self.query_one(f"#tab-{new_session.id}", TabPane)
            await pane_widget.mount(VerticalScroll(id=f"chat-{new_session.id}", classes="session-chat"))

        self.sessions.remove(closing)
        self.active_session = self.sessions[0]

        tabs = self.query_one("#tabs", TabbedContent)
        await tabs.remove_pane(f"tab-{closing.id}")

        self._save_sessions()
        self._refresh_header()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Append the user's message to the active chat when Enter is pressed."""
        if event.input.id != "chat_input":
            return
        text = event.value.strip()
        if not text:
            return
        chat = self._active_chat()
        chat.mount(Markdown(f"**user>** {text}"))
        chat.scroll_end(animate=False)
        event.input.value = ""

    def _refresh_header(self) -> None:
        """Update the application title bar with the active workspace and project."""
        ws = self.active_session.workspace
        prj = self.active_session.project
        ws_name = ws.name if ws else "Sin workspace"
        prj_name = prj.name if prj else "Sin projecto"
        self.title = f"Asistente  ·  {ws_name} / {prj_name}"
        self.sub_title = ""

if __name__ == "__main__":
    MainApp().run()
