"""Medication catalog category registry.

Centralises discovery and aggregation of all category modules.
Adding a new therapeutic category only requires:

1. Create ``categories/<name>.py`` with a ``get_entries()`` function.
2. Register it in ``categories/__init__.py``.

No existing files need modification (Open/Closed Principle).

Author: Bernard Uriza Orozco
Card: FI-RX-004
"""

from __future__ import annotations

from types import ModuleType

from backend.domain.prescription.models.catalog import MedicationCatalogEntry


class CatalogRegistry:
    """Collects ``MedicationCatalogEntry`` instances from category modules.

    Each registered module must expose a ``get_entries`` callable that
    returns ``list[MedicationCatalogEntry]``.
    """

    def __init__(self) -> None:
        self._providers: list[ModuleType] = []

    # -- registration --------------------------------------------------------

    def register(self, module: ModuleType) -> None:
        """Register a category provider module.

        Raises:
            TypeError: If the module lacks a ``get_entries`` callable.
        """
        if not callable(getattr(module, "get_entries", None)):
            msg = (
                f"Module {module.__name__!r} does not expose a "
                f"callable 'get_entries'"
            )
            raise TypeError(msg)
        self._providers.append(module)

    def register_all(self, *modules: ModuleType) -> None:
        """Register multiple provider modules at once."""
        for module in modules:
            self.register(module)

    # -- retrieval -----------------------------------------------------------

    def collect(self) -> list[MedicationCatalogEntry]:
        """Aggregate entries from every registered provider.

        Returns:
            A flat list of all ``MedicationCatalogEntry`` items,
            preserving registration order.
        """
        entries: list[MedicationCatalogEntry] = []
        for provider in self._providers:
            entries.extend(provider.get_entries())
        return entries

    @property
    def provider_count(self) -> int:
        """Number of registered category providers."""
        return len(self._providers)
