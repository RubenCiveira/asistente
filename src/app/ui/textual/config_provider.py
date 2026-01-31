"""Interface for configuration providers.

A :class:`ConfigProvider` supplies a single :class:`~.config_dialog.ConfigPage`
(which may contain children) together with its initial values, and receives the
full configuration dictionary when the user applies or accepts changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from app.ui.textual.widgets.config_dialog import ConfigPage, ConfigValues


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
