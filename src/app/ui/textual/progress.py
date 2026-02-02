"""Progress monitoring UI helpers."""

from __future__ import annotations

from threading import Lock
from typing import Any, Callable, List, Optional

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, ProgressBar, Static

from app.context.progress import ProgressMonitor
from app.ui.textual.widgets.report import Report


class UiProgressMonitor(ProgressMonitor):
    def __init__(self) -> None:
        self._lock = Lock()
        self._total_pending = 0
        self._completed = 0
        self._message = ""
        self._title = "Progress"
        self._errors: List[str] = []
        self._done = False
        self._listeners: List[Callable[["UiProgressMonitor"], None]] = []

    @property
    def total_pending(self) -> int:
        with self._lock:
            return self._total_pending

    @property
    def progress_percent(self) -> float:
        with self._lock:
            if self._total_pending <= 0:
                return 0.0
            ratio = min(1.0, self._completed / self._total_pending)
            return ratio * 100.0

    @property
    def message(self) -> str:
        with self._lock:
            return self._message

    @property
    def title(self) -> str:
        with self._lock:
            return self._title

    @property
    def error_count(self) -> int:
        with self._lock:
            return len(self._errors)

    @property
    def completed(self) -> int:
        with self._lock:
            return self._completed

    @property
    def done(self) -> bool:
        with self._lock:
            return self._done

    def set_total_pending(self, total: int) -> None:
        with self._lock:
            self._total_pending = max(0, total)
            if self._completed > self._total_pending:
                self._completed = self._total_pending
            self._update_done()
        self._notify()

    def set_completed(self, completed: int) -> None:
        with self._lock:
            self._completed = max(0, completed)
            self._update_done()
        self._notify()

    def advance(self, delta: int = 1) -> None:
        with self._lock:
            self._completed = max(0, self._completed + delta)
            self._update_done()
        self._notify()

    def set_message(self, message: str) -> None:
        with self._lock:
            self._message = message
        self._notify()

    def finish(self) -> None:
        with self._lock:
            if self._total_pending > 0:
                self._completed = self._total_pending
            self._done = True
        self._notify()

    def set_title(self, title: str) -> None:
        with self._lock:
            self._title = title
        self._notify()

    def add_error(self, message: str) -> None:
        with self._lock:
            self._errors.append(message)
        self._notify()

    def subscribe(self, listener: Callable[["UiProgressMonitor"], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsubscribe

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener(self)

    def _update_done(self) -> None:
        if self._total_pending > 0 and self._completed >= self._total_pending:
            self._done = True


class ProgressDialog(ModalScreen[None]):
    DEFAULT_CSS = """
    ProgressDialog {
        align: center middle;
        background: $surface 80%;
    }

    #progress-dialog {
        width: 70%;
        max-width: 90;
        min-width: 40;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }

    #progress-title { text-style: bold; margin-bottom: 1; }
    #progress-message { margin-bottom: 1; }
    #progress-summary { margin-top: 1; }
    #progress-buttons { margin-top: 1; align: right middle; height: auto; }
    """

    def __init__(self, monitor: UiProgressMonitor) -> None:
        super().__init__()
        self._monitor = monitor
        self._unsubscribe: Optional[Callable[[], None]] = None

    def compose(self):
        with Vertical(id="progress-dialog"):
            yield Static("Progress", id="progress-title")
            yield Static("", id="progress-message")
            yield ProgressBar(total=100, id="progress-bar")
            yield Static("", id="progress-summary")
            with Horizontal(id="progress-buttons"):
                yield Button("Close", id="progress-close", variant="primary")

    def on_mount(self) -> None:
        self._unsubscribe = self._monitor.subscribe(self._on_monitor_update)
        self._refresh()

    def on_unmount(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "progress-close":
            self.dismiss(None)

    def _on_monitor_update(self, monitor: UiProgressMonitor) -> None:
        if self.app:
            self.app.call_from_thread(self._refresh)

    def _refresh(self) -> None:
        message = self._monitor.message or "Working..."
        percent = self._monitor.progress_percent
        total = self._monitor.total_pending
        completed = self._monitor.completed
        title = self._monitor.title or "Progress"
        errors = self._monitor.error_count

        self.query_one("#progress-title", Static).update(title)
        self.query_one("#progress-message", Static).update(message)
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.total = 100
        bar.progress = percent
        self.query_one(
            "#progress-summary",
            Static,
        ).update(f"{completed}/{total} ({percent:.1f}%)  Errors: {errors}")

        close = self.query_one("#progress-close", Button)
        close.disabled = False


class ProgressButton(Button):
    DEFAULT_CSS = """
    ProgressButton {
        padding: 0 1;
        width: 24;
        min-width: 24;
        height: 1;
        content-align: left middle;
    }

    ProgressButton.-flat {
        border: none;
        background: transparent;
    }
    """

    def __init__(self, id: str = "progress_button") -> None:
        super().__init__("Progress", id=id, variant="default")
        self.add_class("-flat")
        self._monitors: List[UiProgressMonitor] = []
        self._active: Optional[UiProgressMonitor] = None
        self._workers: List[Any] = []

    def add(self, callback: Callable[[UiProgressMonitor], None]) -> UiProgressMonitor:
        monitor = UiProgressMonitor()
        self._monitors.append(monitor)
        self._set_active(monitor)
        if self.app:
            worker = self.app.run_worker(lambda: callback(monitor), thread=True)
            self._workers.append(worker)
        return monitor

    def stop_all(self) -> None:
        for worker in list(self._workers):
            try:
                worker.cancel()
            except Exception:
                pass
        self._workers.clear()

    def on_unmount(self) -> None:
        self.stop_all()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._active is None:
            if self.app:
                self.app.push_screen(
                    Report(
                        message="No active tasks yet.",
                        level="info",
                    )
                )
            return
        if self.app:
            self.app.push_screen(ProgressDialog(self._active))

    def _set_active(self, monitor: UiProgressMonitor) -> None:
        self._active = monitor
        monitor.subscribe(self._on_monitor_update)
        self._update_label(monitor)

    def _on_monitor_update(self, monitor: UiProgressMonitor) -> None:
        if self.app:
            self.app.call_from_thread(self._update_label, monitor)
        if monitor.done:
            self._select_next_pending()

    def _select_next_pending(self) -> None:
        if self._active and not self._active.done:
            return
        for monitor in self._monitors:
            if not monitor.done:
                self._active = monitor
                return

    def _update_label(self, monitor: UiProgressMonitor) -> None:
        percent = monitor.progress_percent
        message = monitor.message or "Progress"
        if monitor.done:
            label = f"{message} (done)"
        else:
            label = f"{message} ({percent:.0f}%)"
        self.label = self._truncate(label, 22)

    def _truncate(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max(0, max_length - 1)] + "…"
