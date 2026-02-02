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

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence

from textual.containers import VerticalScroll
from textual.widgets import Static, Tree

from app.ui.textual.widgets.config_dialog import ConfigPage, ConfigDialog, ConfigValues
from app.ui.textual.widgets.report import Report

class ConfigProvider(ABC):
    """Abstract base class for configuration page providers.

    Implementors supply a page definition and its initial values, and handle
    persistence when the dialog is applied or accepted.
    """

    @abstractmethod
    def config_page(self) -> ConfigPage:
        """Return the configuration page for this provider."""
        ...

    def config_values(self) -> ConfigValues:
        """Return initial values for this provider's page.

        Override to pre-populate form fields with current settings.  The
        default implementation returns empty values.
        """
        return ConfigValues()

    @abstractmethod
    def save_config(self, values: Dict[str, ConfigValues]) -> None:
        """Persist configuration changes.

        Called with the *entire* configuration dictionary (all providers'
        pages) when the user clicks Apply or Accept.

        Args:
            values: Mapping of page id to :class:`ConfigValues`.
        """
        ...

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
        providers: Sequence[ConfigProvider],
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
    # Page reload
    # ------------------------------------------------------------------

    async def _reload_pages(self) -> None:
        """Re-fetch pages and values from providers and rebuild the dialog.

        Called after *Apply* so that pages whose schemas or values depend
        on the just-saved configuration are refreshed (e.g. topic selection
        lists that depend on the global topic definitions).
        """
        current_id = self._current_page.id if self._current_page else None

        # Clear form area first — await ensures old widgets are fully removed
        # before new ones with the same IDs are mounted.
        container = self.query_one("#config-form-area", VerticalScroll)
        await container.remove_children()

        # Re-collect pages and values from providers
        self._pages = [p.config_page() for p in self._providers]
        self._initial_values = {
            page.id: provider.config_values()
            for page, provider in zip(self._pages, self._providers)
        }

        # Rebuild internal indexes
        self._page_index.clear()
        self._parent_map.clear()
        self._page_values.clear()
        self._index_pages(self._pages, None)
        self._load_initial_values()

        # Rebuild tree
        tree = self.query_one("#config-tree", Tree)
        tree.clear()
        self._build_tree()

        # Re-render current page (or first page if no longer exists)
        if current_id and current_id in self._page_index:
            self._current_page = self._page_index[current_id]
        elif self._pages:
            self._current_page = self._pages[0]
        else:
            self._current_page = None

        if self._current_page:
            self._render_page_form(self._current_page)

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
        try:
            self._notify_providers(values)
        except Exception as exc:
            message = str(exc).strip()
            if not message:
                message = "Failed to save configuration."
            self.app.push_screen(
                Report(
                    message=message,
                    level="error",
                    exception=exc,
                )
            )
            return
        self.post_message(self.Applied(values))
        self.run_worker(self._reload_pages())

    def _accept(self) -> None:
        errors = self._validate_all()
        if errors:
            self.query_one("#config-errors", Static).update(
                "\n".join(f"* {e}" for e in errors)
            )
            return
        values = self._collect_all_values()
        try:
            self._notify_providers(values)
        except Exception as exc:
            message = str(exc).strip()
            if not message:
                message = "Failed to save configuration."
            self.app.push_screen(
                Report(
                    message=message,
                    level="error",
                    exception=exc,
                )
            )
            return
        self.dismiss(values)
