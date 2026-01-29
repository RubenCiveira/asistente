from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Markdown, TabbedContent, TabPane
from textual.containers import Vertical, VerticalScroll
from app.ui.textual.action.select_project import SelectProject
from app.ui.textual.action.select_workspace import SelectWorkspace
from app.ui.textual.confirm import Confirm
from app.config import AppConfig
from app.context.workspace import Workspace
from app.context.project import Project
from app.context.session import Session

class MainApp(App):
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
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        self._session_counter = 0

        saved = self.config.sessions
        if saved:
            self.sessions = [self._make_session() for _ in saved]
        else:
            self.sessions = [self._make_session()]

        idx = max(0, min(self.config.active_session_index, len(self.sessions) - 1))
        self.active_session = self.sessions[idx]

        self._select_project_action = SelectProject(self)
        self._select_workspace_action = SelectWorkspace(self, self._select_project_action)

    def _make_session(self) -> Session:
        sid = f"session-{self._session_counter}"
        self._session_counter += 1
        return Session(id=sid)

    # ---- acceso para las acciones ----

    def get_active_workspace(self):
        return self.active_session.workspace

    def get_active_project(self):
        return self.active_session.project

    # ---- mutacion ----

    def select_workspace(self, ws):
        self.active_session.workspace = ws
        self.active_session.project = None
        self.config.set_active_workspace(ws.root_dir)
        self._update_tab_label(self.active_session)
        self._save_sessions()
        self._refresh_header()

    def select_project(self, prj):
        self.active_session.workspace.set_active_project(prj.root_dir)
        self.active_session.project = prj
        self._update_tab_label(self.active_session)
        self._save_sessions()
        self._refresh_header()

    # ---- persistencia de sesiones ----

    def _save_sessions(self) -> None:
        self.config.sessions = [
            {
                "workspace": str(s.workspace.root_dir) if s.workspace else None,
                "project": str(s.project.root_dir) if s.project else None,
            }
            for s in self.sessions
        ]
        self.config.active_session_index = self.sessions.index(self.active_session)
        self.config.save()

    # ---- echo / log ----

    def echo(self, result: Markdown | None):
        if result is not None:
            chat = self._active_chat()
            chat.mount(result)
            chat.scroll_end(animate=False)

    def _log(self, text: str) -> None:
        chat = self._active_chat()
        chat.mount(Markdown(text))
        chat.scroll_end(animate=False)

    def _active_chat(self) -> VerticalScroll:
        return self.query_one(f"#chat-{self.active_session.id}", VerticalScroll)

    # ---- lifecycle ----

    def on_mount(self) -> None:
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
        yield Header()
        with Vertical():
            with TabbedContent(id="tabs"):
                for session in self.sessions:
                    with TabPane(self._tab_label(session), id=f"tab-{session.id}"):
                        yield VerticalScroll(id=f"chat-{session.id}", classes="session-chat")
            yield Input(placeholder="Escribe aqui... (Enter para enviar)", id="prompt")
            yield Footer()

    # ---- tabs ----

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane_id = event.pane.id or ""
        sid = pane_id.removeprefix("tab-")
        for s in self.sessions:
            if s.id == sid:
                self.active_session = s
                break
        self._refresh_header()

    def _tab_label(self, session: Session) -> str:
        if session.project:
            return session.project.name
        if session.workspace:
            return session.workspace.name
        return "Nueva sesion"

    def _update_tab_label(self, session: Session) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tab = tabs.get_tab(f"tab-{session.id}")
        tab.label = self._tab_label(session)

    # ---- actions ----

    def action_select_project(self):
        self.run_worker(self._select_project_action.run())

    def action_select_workspace(self):
        self.run_worker(self._select_workspace_action.run())

    def action_new_session(self):
        self.run_worker(self._new_session())

    async def _new_session(self):
        session = self._make_session()
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

    def action_close_session(self):
        self.run_worker(self._close_session())

    async def _close_session(self):
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
            new_session = self._make_session()
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

    # ---- input ----

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "prompt":
            return
        text = event.value.strip()
        if not text:
            return
        chat = self._active_chat()
        chat.mount(Markdown(f"**user>** {text}"))
        chat.scroll_end(animate=False)
        event.input.value = ""

    # ---- header ----

    def _refresh_header(self) -> None:
        ws = self.active_session.workspace
        prj = self.active_session.project
        ws_name = ws.name if ws else "Sin workspace"
        prj_name = prj.name if prj else "Sin projecto"
        self.title = f"Asistente  ·  {ws_name} / {prj_name}"
        self.sub_title = ""

if __name__ == "__main__":
    MainApp().run()
