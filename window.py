from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown, Label
from textual.containers import Vertical, Horizontal, VerticalScroll
from app.ui.textual.action.select_project import SelectProject
from app.ui.textual.action.select_workspace import SelectWorkspace
from app.config import AppConfig, default_workspaces_dir
from app.context.workspace import Workspace
from app.context.project import Project

class MainApp(App):
    CSS = """
    #chat {
        height: 1fr;
        border: round $primary;
        padding: 1 2;
        overflow-y: auto;
    }

    #prompt {
        border: round $accent;
    }

    #status_bar {
        dock: bottom;
        height: 1;
    }
    """

    BINDINGS = [
        ("ctrl+w", "select_workspace", "Workspace"),
        ("ctrl+y", "select_project", "Project"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        self.current_workspace = None
        self.current_project = None
        self._select_project_action = SelectProject(self)
        self._select_workspace_action = SelectWorkspace(self, self._select_project_action)

    def echo(self, result: Markdown | None):
        if result is not None:
            chat = self.query_one("#chat", VerticalScroll)
            chat.mount(result)
            chat.scroll_end(animate=False)

    def on_mount(self) -> None:
        if self.config.active_workspace and self.config.active_workspace.exists():
            try:
                ws = Workspace.load_or_create(self.config.active_workspace)
                self.current_workspace = ws
                if ws.active_project and ws.active_project.exists():
                    prj = Project.load_or_create(ws.active_project)
                    self.current_project = prj
            except Exception:
                pass
        self._refresh_header()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with VerticalScroll(id="chat"):
                yield Markdown("Listo. Aquí irá el chat/log en **Markdown**.")
            yield Input(placeholder="Escribe aquí… (Enter para enviar)", id="prompt")
            yield Footer()

    def select_workspace(self, ws):
        self.current_workspace = ws
        self.sub_title = ws.name
        self.config.set_active_workspace(ws.root_dir)
        self.config.save()
        self._refresh_header()

    def select_project(self, prj):
        self.current_workspace.set_active_project(prj.root_dir)
        self.current_project = prj
        self._refresh_header()

    def action_select_project(self):
        self.run_worker( self._select_project_action.run() )

    def action_select_workspace(self):
        self.run_worker( self._select_workspace_action.run() )

    # async def on_button_pressed(self, event: Button.Pressed) -> None:
    #     if event.button.id == "clear_chat":
    #         chat = self.query_one("#chat", VerticalScroll)
    #         chat.remove_children()

    #     if event.button.id == "open_form":
    #         self.run_worker( self.test_form.run() )
    #     if event.button.id == "select_file":
    #         self.run_worker( self.test_path.run() )
    #     if event.button.id == "select_workspace":
    #         self.run_worker( self._select_workspace_action.run() )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "prompt":
            return
        text = event.value.strip()
        if not text:
            return
        chat = self.query_one("#chat", VerticalScroll)
        chat.mount(Markdown(f"**user>** {text}"))
        chat.scroll_end(animate=False)
        event.input.value = ""

    def _log(self, text: str) -> None:
        chat = self.query_one("#chat", VerticalScroll)
        chat.mount(Markdown(text))
        chat.scroll_end(animate=False)

    def _refresh_header(self) -> None:
        ws = self.current_workspace.name if self.current_workspace else "Sin workspace"
        pr = self.current_project.name if self.current_project else "Sin projecto"

        self.title = f"Asistente  ·  {ws} / {pr}"
        self.sub_title = ""
        # header.sub_title = str(self.workspace.root_dir) if self.workspace else ""

if __name__ == "__main__":
    MainApp().run()
