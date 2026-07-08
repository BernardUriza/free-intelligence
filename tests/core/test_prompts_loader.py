"""Tests for the prompts_loader — mtime-aware reads from insult/prompts/*.md.

These run against the REAL prompts directory (no temp dir) because the
loader resolves paths from `__file__`. Tests that need to mutate prompts
write to a temp file and monkey-patch _PROMPTS_DIR for that test only."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from personas.insult.core import prompts_loader
from personas.insult.core.prompts_loader import (
    clear_prompt_cache,
    list_available_prompts,
    load_prompt,
)


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Each test starts with an empty cache so mtime tests aren't masked
    by cross-test residue."""
    clear_prompt_cache()
    yield
    clear_prompt_cache()


def test_load_prompt_returns_real_content():
    """The migrated prompts MUST be loadable. If one is missing, the
    deploy would crash on the first LLM call — better catch it here."""
    text = load_prompt("facts_extraction")
    assert isinstance(text, str)
    assert len(text) > 100
    assert "fact extractor" in text


def test_load_prompt_strips_trailing_newline():
    """Editors leave a trailing newline; the loader normalizes that out
    so callers don't see double newlines when concatenating."""
    text = load_prompt("facts_extraction")
    assert not text.endswith("\n")


def test_load_prompt_file_not_found_raises_with_helpful_message():
    """Typos crash loud. The exception lists available prompts so the
    operator can spot the typo immediately."""
    with pytest.raises(FileNotFoundError) as exc:
        load_prompt("definitely_not_a_real_prompt_xyz")
    msg = str(exc.value)
    assert "definitely_not_a_real_prompt_xyz" in msg
    assert "Available:" in msg


def test_list_available_prompts_includes_all_migrated():
    """Sanity: every prompt the codebase calls load_prompt() for must
    actually exist on disk."""
    available = set(list_available_prompts())
    expected = {
        "facts_extraction",
        "language_cure",
        "memory_consolidator_judge",
        "proactive_social",
        "proactive_world_scan",
        "siesta_diary",
    }
    missing = expected - available
    assert not missing, f"missing prompts on disk: {missing}"


def test_list_available_prompts_returns_sorted():
    available = list_available_prompts()
    assert available == sorted(available)


# ---------------------------------------------------------------------------
# mtime-aware caching — the core of the hot-reload feature
# ---------------------------------------------------------------------------


def test_cache_returns_same_string_on_repeat_read():
    """Repeat read with no file change — should be cache hit, identical
    string returned (object equality, not just equal value)."""
    a = load_prompt("language_cure")
    b = load_prompt("language_cure")
    assert a == b


def test_cache_invalidates_when_file_mtime_changes(tmp_path, monkeypatch):
    """Operator edits a .md and saves; loader must pick up the new content
    on the next call without restart."""
    fake_dir = tmp_path / "prompts"
    fake_dir.mkdir()
    p = fake_dir / "test_prompt.md"
    p.write_text("first version\n", encoding="utf-8")

    monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", fake_dir)
    clear_prompt_cache()

    first = load_prompt("test_prompt")
    assert first == "first version"

    # Sleep enough to advance mtime even on filesystems with 1s granularity
    time.sleep(1.1)
    p.write_text("second version after edit\n", encoding="utf-8")

    second = load_prompt("test_prompt")
    assert second == "second version after edit"


def test_cache_does_not_reread_when_mtime_unchanged(tmp_path, monkeypatch):
    """Performance contract: when mtime hasn't changed, no disk read.
    Stress test for the hot-path case."""
    fake_dir = tmp_path / "prompts"
    fake_dir.mkdir()
    p = fake_dir / "perf_prompt.md"
    p.write_text("content\n", encoding="utf-8")

    monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", fake_dir)
    clear_prompt_cache()
    # Prime the cache
    load_prompt("perf_prompt")

    call_count = {"reads": 0}
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        call_count["reads"] += 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    # 10 calls without file change — should all be cache hits
    for _ in range(10):
        load_prompt("perf_prompt")
    assert call_count["reads"] == 0  # zero new reads after primer


def test_clear_prompt_cache_forces_rereads(tmp_path, monkeypatch):
    """Tests that need to verify reload behavior call clear_prompt_cache
    to bypass mtime granularity issues."""
    fake_dir = tmp_path / "prompts"
    fake_dir.mkdir()
    (fake_dir / "tiny.md").write_text("v1", encoding="utf-8")

    monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", fake_dir)
    clear_prompt_cache()

    # Prime
    assert load_prompt("tiny") == "v1"

    # Rewrite with same length but different content
    (fake_dir / "tiny.md").write_text("v2", encoding="utf-8")
    clear_prompt_cache()
    assert load_prompt("tiny") == "v2"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_load_prompt_preserves_internal_newlines(tmp_path, monkeypatch):
    """Multi-line prompts are the norm; only the FINAL trailing newline is
    stripped, not internal ones."""
    fake_dir = tmp_path / "prompts"
    fake_dir.mkdir()
    (fake_dir / "multi.md").write_text("line one\nline two\nline three\n", encoding="utf-8")

    monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", fake_dir)
    clear_prompt_cache()
    text = load_prompt("multi")
    assert text == "line one\nline two\nline three"


def test_load_prompt_handles_no_trailing_newline(tmp_path, monkeypatch):
    """A prompt file without a trailing newline is also OK."""
    fake_dir = tmp_path / "prompts"
    fake_dir.mkdir()
    (fake_dir / "no_newline.md").write_text("no trailing newline", encoding="utf-8")

    monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", fake_dir)
    clear_prompt_cache()
    assert load_prompt("no_newline") == "no trailing newline"
