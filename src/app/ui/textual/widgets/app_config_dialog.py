"""Application-level configuration dialog driven by providers.

:class:`AppConfigDialog` is a :class:`~.config_dialog.ConfigDialog` subclass
that collects its pages and initial values from a list of
:class:`~.config_provider.ConfigProvider` instances.  When the user clicks
*Apply* or *Accept*, every provider's :meth:`~.config_provider.ConfigProvider.save_config`
method is called with the full configuration dictionary before the normal
dialog behaviour (posting :class:`~.config_dialog.ConfigDialog.Applied` or
dismissing).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from textual.widgets import Static

from app.ui.textual.widgets.config_dialog import ConfigDialog, ConfigValues
from app.ui.textual.widgets.config_provider import ConfigProvider


class AppConfigDialog(ConfigDialog):
    """Configuration dialog assembled from :class:`ConfigProvider` instances.

    Each provider contributes one top-level page (which may have children).
    Initial values are collected via
    :meth:`~ConfigProvider.config_values` and on Apply/Accept every
    provider's :meth:`~ConfigProvider.save_config` is invoked with the
    complete values dictionary.

    Args:
        providers: List of configuration providers.
        title: Dialog title shown at the top.
    """

    def __init__(
        self,
        providers: List[ConfigProvider],
        title: str = "Configuration",
    ) -> None:
        self._providers = list(providers)
        pages = [p.config_page() for p in self._providers]
        initial: Dict[str, ConfigValues] = {
            p.config_page().id: p.config_values()
            for p in self._providers
        }
        super().__init__(pages, initial_values=initial, title=title)

    # ------------------------------------------------------------------
    # Provider notification
    # ------------------------------------------------------------------

    def _notify_providers(self, values: Dict[str, ConfigValues]) -> None:
        """Call :meth:`save_config` on every provider."""
        for provider in self._providers:
            provider.save_config(values)

    # ------------------------------------------------------------------
    # Override apply / accept to notify providers
    # ------------------------------------------------------------------

    def _apply(self) -> None:
        errors = self._validate_all()
        if errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in errors)
            )
            return
        self.query_one("#config-errors", Static).update("")
        values = self._collect_all_values()
        self._notify_providers(values)
        self.post_message(self.Applied(values))

    def _accept(self) -> None:
        errors = self._validate_all()
        if errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in errors)
            )
            return
        values = self._collect_all_values()
        self._notify_providers(values)
        self.dismiss(values)
