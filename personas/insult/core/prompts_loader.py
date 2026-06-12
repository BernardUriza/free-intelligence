"""Prompt loader — read prompts from .md files in `insult/prompts/`.

Why .md and not Python constants:
  • Prompts are CONTENT, not code. Editing them in a Python module forces
    a version bump, escape gymnastics around quotes, and re-reading the
    text in an unfamiliar context.
  • As .md files in their own directory, the operator can diff them
    cleanly in git, edit them in any text editor, and review changes
    without scanning around scaffolding.
  • Each prompt has a stable identity (its filename) that callers
    reference by name, not by import path — so renaming or moving
    prompts later doesn't require touching every caller.

Why mtime-based cache (not lru_cache):
  • Bernard wants to edit a prompt and have the running bot pick up the
    change without a redeploy / restart. Pure lru_cache would lock in
    the first read and ignore subsequent edits.
  • mtime check is cheap (one stat() per call). Read-from-disk is also
    cheap — these are <10KB markdown files. The cache is purely a
    micro-optimization for hot paths; correctness comes from the mtime
    invalidation, not the cache.
  • Tests can call clear_prompt_cache() to force a re-read regardless of
    mtime (useful when a test fixture writes a prompt to disk and the
    filesystem timestamp granularity is coarse).

Usage:
    from personas.insult.core.prompts_loader import load_prompt
    text = load_prompt("moltbook_outbound_draft")
    # → reads insult/prompts/moltbook_outbound_draft.md
"""

from __future__ import annotations

from pathlib import Path

import structlog

log = structlog.get_logger()

# `insult/prompts/` lives next to `insult/core/`, so we resolve from this
# file's parent's parent.
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# name → (mtime_ns, content)
_CACHE: dict[str, tuple[int, str]] = {}


def load_prompt(name: str) -> str:
    """Read `insult/prompts/<name>.md` and return its text content.

    Mtime-aware caching: re-reads from disk when the file's mtime changes,
    so editing the .md and saving picks up immediately without restart.

    Strips a single trailing newline (text editors typically leave one)
    so the prompt content matches what the previous Python triple-quoted
    constants produced. Internal newlines are preserved verbatim.

    Raises FileNotFoundError with a helpful message if the prompt doesn't
    exist — the caller crashes loud rather than silently using an empty
    string and shipping a malformed LLM call to prod."""
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        try:
            available = sorted(p.stem for p in _PROMPTS_DIR.glob("*.md"))
        except Exception:
            available = []
        raise FileNotFoundError(f"prompt {name!r} not found at {path}. Available: {available[:20]}")
    # mtime_ns has nanosecond resolution where supported; on older filesystems
    # it falls back to second resolution. Either way it changes when the file
    # is rewritten, which is what we need.
    mtime_ns = path.stat().st_mtime_ns
    cached = _CACHE.get(name)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    if text.endswith("\n"):
        text = text[:-1]
    _CACHE[name] = (mtime_ns, text)
    log.info("prompt_loaded", name=name, length=len(text), reload=cached is not None)
    return text


def clear_prompt_cache() -> None:
    """Empty the cache. Tests call this when filesystem mtime granularity
    might be too coarse to detect a fast-rewritten file."""
    _CACHE.clear()


def list_available_prompts() -> list[str]:
    """List all prompt names available on disk. Useful for /debug endpoints
    or `python -m insult` operations that want to enumerate prompts."""
    if not _PROMPTS_DIR.exists():
        return []
    return sorted(p.stem for p in _PROMPTS_DIR.glob("*.md"))
