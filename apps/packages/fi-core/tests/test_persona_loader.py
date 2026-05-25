"""Tests for fi_core.persona.loader.PersonaLoader (mtime hot-reload)."""

from __future__ import annotations

import time

import pytest

from fi_core.persona.loader import PersonaLoader


def test_loads_file_text(tmp_path):
    f = tmp_path / "persona.md"
    f.write_text("Eres ALICE.", encoding="utf-8")
    assert PersonaLoader(f).load() == "Eres ALICE."


def test_reloads_on_mtime_change(tmp_path):
    f = tmp_path / "persona.md"
    f.write_text("v1", encoding="utf-8")
    pl = PersonaLoader(f)
    assert pl.load() == "v1"

    # Rewrite with a strictly newer mtime so the change is observable.
    f.write_text("v2", encoding="utf-8")
    future = time.time() + 10
    import os

    os.utime(f, (future, future))
    assert pl.load() == "v2"


def test_caches_when_unchanged(tmp_path):
    f = tmp_path / "persona.md"
    f.write_text("stable", encoding="utf-8")
    pl = PersonaLoader(f)
    first = pl.load()
    # Same mtime → returns the cached object without re-reading.
    second = pl.load()
    assert first == second == "stable"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        PersonaLoader(tmp_path / "nope.md").load()


def test_accepts_str_path(tmp_path):
    f = tmp_path / "persona.md"
    f.write_text("from str path", encoding="utf-8")
    assert PersonaLoader(str(f)).load() == "from str path"


def test_importable_without_mcp_extra():
    """Importing fi_core.persona (for PersonaLoader/detectors) must NOT require the
    `mcp` extra — only touching MCP_SERVER_NAME/MCP_TOOLS pulls it (lazy)."""
    import fi_core.persona as p

    assert p.PersonaLoader is PersonaLoader
    assert p.BreakDetector  # zero-dep detector still eagerly available
