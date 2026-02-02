"""Progress monitoring interface for long-running tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProgressMonitor(ABC):
    """Abstract interface for reporting task progress."""

    @property
    @abstractmethod
    def total_pending(self) -> int:
        """Total units pending for the task."""

    @property
    @abstractmethod
    def progress_percent(self) -> float:
        """Completion percentage between 0.0 and 100.0."""

    @property
    @abstractmethod
    def message(self) -> str:
        """Current operation message."""

    @property
    @abstractmethod
    def title(self) -> str:
        """Task title."""

    @property
    @abstractmethod
    def error_count(self) -> int:
        """Number of errors recorded."""

    @abstractmethod
    def set_total_pending(self, total: int) -> None:
        """Set total units pending for the task."""

    @abstractmethod
    def set_message(self, message: str) -> None:
        """Update the current operation message."""

    @abstractmethod
    def advance(self, delta: int = 1) -> None:
        """Advance progress by *delta* units."""

    @abstractmethod
    def finish(self) -> None:
        """Mark the task as completed."""

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Update the task title."""

    @abstractmethod
    def add_error(self, message: str) -> None:
        """Record an error message for the task."""
