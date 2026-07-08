"""Import sweep over every persona_runner module — the lazy-import time bomb guard.

The 2026-07-08 P0: the v4.22.5 legacy purge deleted personas.insult.core.routing
believing it double-dead, but persona_runner/router_runtime.py imported it — and
runner.py loads router_runtime LAZILY inside the turn function, so the whole CI
suite passed green while every prod /v1/turn would crash with
ModuleNotFoundError. The CD health smoke caught it post-deploy; CI could not,
because nothing ever imported the module.

This sweep makes deletion-behind-a-lazy-import a CI failure: every module in
persona_runner/ must import cleanly, which transitively resolves their top-level
imports. It does not execute any runner logic — import only.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import persona_runner

_MODULES = sorted(m.name for m in pkgutil.iter_modules(persona_runner.__path__, "persona_runner."))


def test_sweep_found_the_known_surface():
    assert "persona_runner.router_runtime" in _MODULES
    assert "persona_runner.model_routing" in _MODULES
    assert len(_MODULES) >= 3


@pytest.mark.parametrize("module_name", _MODULES)
def test_module_imports_clean(module_name):
    importlib.import_module(module_name)
