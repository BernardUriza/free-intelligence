"""Smoke tests for the workspace renderer.

Full Postgres-backed tests live in tests/integration/ (pytest-postgresql
fixture). These tests only check the pure helpers (atomic write,
frontmatter formatting) so they run anywhere without a real database.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_renderer_module_imports():
    """Lazy import so we don't need POSTGRES_URL set to load the module."""
    from persona_runner import workspace_renderer  # noqa: F401


def test_frontmatter_shape(tmp_path: Path):
    """`_frontmatter` produces a parseable YAML block followed by a blank line."""
    from persona_runner.workspace_renderer import _frontmatter

    out = _frontmatter(user_id="x", count=3, when="2026-01-01T00:00:00Z")
    assert out.startswith("---\n")
    assert "user_id: x" in out
    assert "count: 3" in out
    assert "when: 2026-01-01T00:00:00Z" in out
    assert out.endswith("---\n\n")


def test_atomic_write_creates_parents_and_swaps(tmp_path: Path):
    """`_atomic_write` creates the parent dir and replaces the file atomically.

    Verifies the .tmp pattern: at no point should an empty / partial file
    be visible to a reader.
    """
    from persona_runner.workspace_renderer import _atomic_write

    target = tmp_path / "facts" / "deeply" / "nested" / "file.md"
    _atomic_write(target, "hello\nworld\n")
    assert target.exists()
    assert target.read_text() == "hello\nworld\n"
    # No leftover .tmp
    assert not (target.parent / "file.md.tmp").exists()


def test_atomic_write_overwrites_existing(tmp_path: Path):
    """Subsequent writes replace the previous content entirely."""
    from persona_runner.workspace_renderer import _atomic_write

    target = tmp_path / "out.md"
    _atomic_write(target, "first")
    _atomic_write(target, "second")
    assert target.read_text() == "second"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX rename semantics")
def test_atomic_write_no_partial_visible(tmp_path: Path):
    """The replace step is atomic on POSIX. After replace, the file is fully
    populated; there is no window where a reader sees an empty file.

    We can't truly race here in a unit test, but we can at least verify
    the file is non-empty immediately after write returns.
    """
    from persona_runner.workspace_renderer import _atomic_write

    target = tmp_path / "x.md"
    _atomic_write(target, "x" * 10000)
    assert target.stat().st_size == 10000
