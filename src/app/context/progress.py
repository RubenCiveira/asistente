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
