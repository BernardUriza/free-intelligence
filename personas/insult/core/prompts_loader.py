"""Insult's prompt loader — thin binding over the generic `khimeras_shared.prompts`.

The mtime-aware loading machinery is persona-neutral and lives in
`khimeras_shared.prompts` (PR-3b). This module binds it to Insult's prompts
directory (`personas/insult/prompts/`) and keeps the historical public surface
(`load_prompt`, `clear_prompt_cache`, `list_available_prompts`) so the ~14
callers across `personas/insult/` are untouched.

`_PROMPTS_DIR` is read fresh on every call (module-global lookup) so tests can
`monkeypatch.setattr(prompts_loader, "_PROMPTS_DIR", tmp)` and have it take
effect, exactly as before the extraction.

Usage (unchanged):
    from personas.insult.core.prompts_loader import load_prompt
    text = load_prompt("facts_extraction")
    # -> reads personas/insult/prompts/facts_extraction.md
"""

from __future__ import annotations

from pathlib import Path

from khimeras_shared.prompts import PromptCache
from khimeras_shared.prompts import list_available as _list_available
from khimeras_shared.prompts import load_prompt as _load_prompt

# `prompts/` lives next to `core/`, so resolve from this file's parent's parent.
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_CACHE: PromptCache = {}


def load_prompt(name: str) -> str:
    """Read `personas/insult/prompts/<name>.md`. Mtime-aware, hot-reloads on edit."""
    return _load_prompt(_PROMPTS_DIR, name, _CACHE)


def clear_prompt_cache() -> None:
    """Empty the cache — tests call this when filesystem mtime granularity is coarse."""
    _CACHE.clear()


def list_available_prompts() -> list[str]:
    """List all Insult prompt names available on disk."""
    return _list_available(_PROMPTS_DIR)
