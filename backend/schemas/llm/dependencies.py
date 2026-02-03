"""FastAPI Dependency Injection providers for LLM Schemas.

Provides singleton IPresetLoader dependency.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.schemas.llm.interfaces.ipreset_loader import IPresetLoader


@lru_cache(maxsize=1)
def _get_preset_loader_singleton() -> "IPresetLoader":
    """Internal singleton factory for PresetLoader."""
    from backend.schemas.llm.preset_loader import PresetLoader

    return PresetLoader()


def get_preset_loader_dep() -> "IPresetLoader":
    """Get preset loader singleton for workers.

    Returns:
        IPresetLoader singleton (same instance for all calls)

    Note:
        Replaces deprecated get_preset_loader() service locator.
        Workers receive this as a constructor parameter.
    """
    return _get_preset_loader_singleton()


__all__ = ["get_preset_loader_dep"]
