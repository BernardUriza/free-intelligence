"""Import-smoke harness — a green suite must not hide an import-broken module.

Why this exists (2026-07-14, the castigo): `persona_core/deep_memory.py` was
resurrected two commits AFTER its dependency `corpus/film_references.py` was
deleted as "zero consumers". The module crashed with ModuleNotFoundError at
runtime (the runner's deep_memory MCP tool), but its tests had died in the same
purge — so 590 green tests said nothing. Walking-import every module makes a
dangling import a RED test the moment it lands, not a prod discovery.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import demux_ai
import persona_core
import persona_gateway
import shared

_PACKAGES = [persona_core, shared, demux_ai, persona_gateway]


def _all_modules() -> list[str]:
    names: list[str] = []
    for pkg in _PACKAGES:
        names.append(pkg.__name__)
        names.extend(m.name for m in pkgutil.walk_packages(pkg.__path__, f"{pkg.__name__}."))
    return sorted(names)


@pytest.mark.parametrize("module_name", _all_modules())
def test_module_imports_cleanly(module_name: str):
    importlib.import_module(module_name)
