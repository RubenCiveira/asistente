"""Textual TUI entry point providing a tabbed multi-session chat interface.

Each tab corresponds to a :class:`~app.context.session.Session` that binds a
workspace and a project.  The application persists open sessions to disk so
that they are restored on the next launch.

Keyboard shortcuts:
    Ctrl+W  Select workspace
    Ctrl+Y  Select project
    Ctrl+N  Open a new session tab
    Ctrl+D  Close the active session tab
    Ctrl+S  Settings
    Ctrl+Q  Quit
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, LoadingIndicator, Markdown, TabbedContent, TabPane, Static
from textual.containers import Horizontal, Vertical, VerticalScroll
from rich.text import Text

from app.config import AppConfig
from app.context.workspace import Workspace
from app.context.project import Project
from app.context.session import Session
from app.context.keywords import Keywords


from app.ui.textual.widgets.confirm import Confirm
from app.ui.textual.chat_input import ChatInput
from app.ui.textual.action.select_project import SelectProject
from app.ui.textual.action.select_workspace import SelectWorkspace
from app.ui.textual.action.test.test_config import TestConfig
from app.ui.textual.app_config_dialog import AppConfigDialog
from app.ui.textual.completion_provider.slash_provider import SlashCommandProvider
from app.ui.textual.completion_provider.at_provider import ContextProvider
from app.ui.textual.completion_provider.colon_provider import PowerCommandProvider
from app.ui.textual.completion_provider.hash_provider import SemanticProvider
from app.ui.textual.config_provider.rag_config_provider import RagConfigProvider
from app.ui.textual.progress import ProgressButton

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

    #status_bar {
        height: 2;
        padding: 0 1;
        align-vertical: middle;
    }

    #status_label {
        content-align: left middle;
    }

    #status_loading {
        width: 3;
        height: 1;
        margin-right: 1;
    }

    #status_spacer {
        width: 1fr;
    }

    #status_actions {
        width: auto;
        align: right middle;
        height: 1;
    }
    """

    BINDINGS = [
        ("ctrl+w", "select_workspace", "Workspace"),
        ("ctrl+y", "select_project", "Project"),
        ("ctrl+n", "new_session", "New tab"),
        ("ctrl+d", "close_session", "Close tab"),
        ("ctrl+k", "clear_text", "Clear text"),
        ("ctrl+t", "test_config", "Test config"),
        ("ctrl+s", "settings", "Settings"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialise the app, restoring sessions from the persisted config."""
        super().__init__()
        self.config = AppConfig.load()

        saved = self.config.sessions
        if saved:
            self.sessions = []
            for s in saved:
                sid = s.get("id")
                if isinstance(sid, str) and sid:
                    self.sessions.append(Session(config=self.config, id=sid))
                else:
                    self.sessions.append(Session(config=self.config))
        else:
            self.sessions = [Session(config=self.config)]

        for session in self.sessions:
            self._bind_session(session)

        idx = max(0, min(self.config.active_session_index, len(self.sessions) - 1))
        self.config.active_session = self.sessions[idx]

        self._select_project_action = SelectProject(self)
        self._select_workspace_action = SelectWorkspace(self, self._select_project_action)
        self._test_config_action = TestConfig(self)

    def get_active_workspace(self):
        """Return the workspace of the active session (may be ``None``)."""
        return self.config.active_session.workspace

    def get_active_project(self):
        """Return the project of the active session (may be ``None``)."""
        return self.config.active_session.project

    def select_workspace(self, ws) -> None:
        """Set *ws* as the active workspace, clear the project and persist."""
        self.config.active_session.workspace = ws
        self.config.active_session.project = None
        self.config.set_active_workspace(ws.root_dir)
        self._update_tab_label(self.config.active_session)
        self._save_sessions()
        self._refresh_header()

    def select_project(self, prj) -> None:
        """Set *prj* as the active project and persist."""
        if not self.config.active_session.workspace:
            return
        self.config.active_session.workspace.set_active_project(prj.root_dir)
        self.config.active_session.project = prj
        self._update_tab_label(self.config.active_session)
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
        self.config.active_session_index = self.sessions.index(self.config.active_session)
        self.config.save()

    def echo(self, result: Markdown | str | None) -> None:
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
        return self.query_one(f"#chat-{self.config.active_session.id}", VerticalScroll)

    def on_mount(self) -> None:
        """Restore workspace/project references for every session from config."""
        saved = self.config.sessions
        vt = self.config.topic_names()
        for i, session in enumerate(self.sessions):
            if i < len(saved):
                ws_path = saved[i].get("workspace")
                prj_path = saved[i].get("project")
                if ws_path:
                    p = Path(ws_path)
                    if p.exists():
                        try:
                            ws = Workspace.load_or_create(p, valid_topics=vt)
                            session.workspace = ws
                            if prj_path:
                                pp = Path(prj_path)
                                if pp.exists():
                                    prj = Project.load_or_create(pp, valid_topics=vt)
                                    session.project = prj
                        except Exception:
                            pass

        # Compatibilidad: si no habia sesiones guardadas, cargar workspace por defecto
        if not saved and self.config.active_workspace and self.config.active_workspace.exists():
            try:
                ws = Workspace.load_or_create(self.config.active_workspace, valid_topics=vt)
                self.config.active_session.workspace = ws
                if ws.active_project and ws.active_project.exists():
                    prj = Project.load_or_create(ws.active_project, valid_topics=vt)
                    self.config.active_session.project = prj
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
        self.progress_button = ProgressButton(id="progress_button")
        yield Header()
        with Vertical():
            with TabbedContent(id="tabs"):
                for session in self.sessions:
                    with TabPane(self._tab_label(session), id=f"tab-{session.id}"):
                        yield VerticalScroll(id=f"chat-{session.id}", classes="session-chat")
            # yield Input(placeholder="Escribe aqui... (Enter para enviar)", id="prompt")
            yield chat
            with Horizontal(id="status_bar"):
                yield LoadingIndicator(id="status_loading")
                yield Static("", id="status_label")
                yield Static("", id="status_spacer")
                with Horizontal(id="status_actions"):
                    yield self.progress_button
            yield Footer()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Update :attr:`active_session` and the header when the user switches tabs."""
        pane_id = event.pane.id or ""
        sid = pane_id.removeprefix("tab-")
        for s in self.sessions:
            if s.id == sid:
                self.config.active_session = s
                break
        self._render_session(self.config.active_session)
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
        """Keybinding action: clear all messages from the active chat area."""
        self.config.active_session.clear()

    def action_select_project(self) -> None:
        """Keybinding action: launch the project-selection flow."""
        self.run_worker(self._select_project_action.run())

    def action_select_workspace(self) -> None:
        """Keybinding action: launch the workspace-selection flow."""
        self.run_worker(self._select_workspace_action.run())

    def action_test_config(self) -> None:
        """Keybinding action: launch the configuration dialog smoke test."""
        self.run_worker(self._test_config_action.run())

    def action_settings(self) -> None:
        """Keybinding action: open the application settings dialog."""
        self.run_worker(self._open_settings())

    async def _open_settings(self) -> None:
        """Open the :class:`AppConfigDialog` with the RAG config provider."""
        providers = [RagConfigProvider(self)]
        await self.push_screen_wait(AppConfigDialog(providers))

    def action_new_session(self) -> None:
        """Keybinding action: create a new empty session tab."""
        self.run_worker(self._new_session())

    async def _new_session(self) -> None:
        """Create a new session, add a tab for it and activate it."""
        session = Session(config=self.config)
        self._bind_session(session)
        self.sessions.append(session)

        tabs = self.query_one("#tabs", TabbedContent)
        pane = TabPane(self._tab_label(session), id=f"tab-{session.id}")
        await tabs.add_pane(pane)

        pane_widget = self.query_one(f"#tab-{session.id}", TabPane)
        await pane_widget.mount(VerticalScroll(id=f"chat-{session.id}", classes="session-chat"))

        tabs.active = f"tab-{session.id}"
        self.config.active_session = session
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

        closing = self.config.active_session
        was_last = len(self.sessions) == 1

        if was_last:
            new_session = Session(config=self.config)
            self._bind_session(new_session)
            new_session.workspace = closing.workspace
            new_session.project = closing.project
            self.sessions.append(new_session)

            tabs = self.query_one("#tabs", TabbedContent)
            pane = TabPane(self._tab_label(new_session), id=f"tab-{new_session.id}")
            await tabs.add_pane(pane)
            pane_widget = self.query_one(f"#tab-{new_session.id}", TabPane)
            await pane_widget.mount(VerticalScroll(id=f"chat-{new_session.id}", classes="session-chat"))

        closing.unsubscribe(self._on_session_change)
        self.sessions.remove(closing)
        self.config.active_session = self.sessions[0]

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
        event.input.value = ""
        self.run_worker(self._ask_session(text))

    async def _ask_session(self, text: str):
        result = await self.config.active_session.ask(text)
        if result is None:
            return
        self.run_worker(self._ask_callback(result))

    async def _ask_callback(self, callback):
        result = await callback()
        if result is None:
            return
        self.run_worker(self._ask_callback(result))

    def _bind_session(self, session: Session) -> None:
        session.subscribe(self._on_session_change)

    def _on_session_change(self, session: Session) -> None:
        self._render_session( session )

    def _render_session(self, session: Session) -> None:
        if session != self.config.active_session:
            return
        chat = self._active_chat()
        chat.remove_children()
        for message in session.messages:
            chat.mount(Markdown(f"**{message.actor}>** {message.msg}"))
        if session.asking:
            chat.mount(Markdown("**assistant>** ..."))
        chat.scroll_end(animate=False)
        self._update_status(session)

    def _update_status(self, session: Session) -> None:
        indicator = self.query_one("#status_loading", LoadingIndicator)
        label = self.query_one("#status_label", Static)
        if session.asking:
            indicator.display = True
            label.display = True
            label.update( session.action )
        else:
            indicator.display = False
            label.display = False
            label.update("")

    def _refresh_header(self) -> None:
        """Update the application title bar with the active workspace and project."""
        ws = self.config.active_session.workspace
        prj = self.config.active_session.project
        ws_name = ws.name if ws else "Sin workspace"
        prj_name = prj.name if prj else "Sin projecto"
        self.title = f"Asistente  ·  {ws_name} / {prj_name}"
        self.sub_title = ""

    def on_exit(self) -> None:
        if hasattr(self, "progress_button"):
            self.progress_button.stop_all()

if __name__ == "__main__":
    MainApp().run()
