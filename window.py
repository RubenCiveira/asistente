from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from app.ui.textual.action.test.test_path import TestPath
from app.ui.textual.action.test.test_form import TestForm
from app.ui.textual.action.select_workspace import SelectWorkspace

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
    """
    def __init__(self):
        super().__init__()
        self.current_workspace = None
        self.test_path = TestPath(self)
        self.test_form = TestForm(self)
        self.select_workspace = SelectWorkspace(self)

    def echo(self, result: Markdown | None):
        if result is not None:
            chat = self.query_one("#chat", VerticalScroll)
            chat.mount(result)
            chat.scroll_end(animate=False)

    # def on_mount(self) -> None:
    #     self.app_config = AppConfig.load()
    #     self.workspace: Workspace | None = None

    #     # Si hay workspace activo, intentamos cargarlo
    #     if self.app_config.active_workspace:
    #         try:
    #             self.workspace = Workspace.load_or_create(
    #                 self.app_config.active_workspace
    #             )
    #             self._log(f"🗂️ Workspace activo: **{self.workspace.name}**")
    #             return
    #         except Exception as e:
    #             self._log(f"⚠️ Error cargando workspace activo: {e}")

    #     # Si NO hay workspace, lanzar selector
    #     self._log("ℹ️ No hay workspace activo. Selecciona uno.")
    #     self.select_workspace_on_startup()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with VerticalScroll(id="chat"):
                yield Markdown("Listo. Aquí irá el chat/log en **Markdown**.")
            with Horizontal():
                yield Button("Open Form", id="open_form", variant="primary")
                yield Button("Select file", id="select_file")
                yield Button("Workspace", id="select_workspace")
                yield Button("Clear", id="clear_chat")
            yield Input(placeholder="Escribe aquí… (Enter para enviar)", id="prompt")
        yield Footer()

    async def on_button_pressed(self, evesolont: Button.Pressed) -> None:
        if event.button.id == "clear_chat":
            chat = self.query_one("#chat", VerticalScroll)
            chat.remove_children()

        if event.button.id == "open_form":
            self.run_worker( self.test_form.run() )
        if event.button.id == "select_file":
            self.run_worker( self.test_path.run() )
        if event.button.id == "select_workspace":
            self.run_worker( self.select_workspace.run() )

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


if __name__ == "__main__":
    MainApp().run()
