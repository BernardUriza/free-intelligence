"""Backwards-compatible shim for the preset vocabulary.

The enums and the classifier-result dataclass moved to
`insult.core.contracts.presets` (a neutral, stdlib-only contracts module) so
host-facing code can depend on them without crossing the host→smart import
boundary. This module re-exports them so existing callers
(`from insult.core.presets.types import PresetMode`, the package barrel, the
patterns/guidance/classifier modules) keep working unchanged.

Enum identity is preserved: every type is defined exactly once in
`insult.core.contracts.presets` and imported here — there is no redefinition.
"""

from __future__ import annotations

from insult.core.contracts.presets import (
    PresetMode,
    PresetModifier,
    PresetSelection,
)

__all__ = [
    "PresetMode",
    "PresetModifier",
    "PresetSelection",
]
