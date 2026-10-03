"""Generic, persona-neutral prompt loader — mtime-aware reads from a `.md` dir.

Why this lives in `persona_core`: loading prompts from `.md` files (so the
operator edits content in git, not Python string constants, and the running bot
hot-reloads on save) is a CAPABILITY both personas want — not Insult-specific. It
is parameterized by the prompts directory, so each persona binds its own dir in a
thin wrapper (e.g. `personas/insult/core/prompts_loader.py`). `persona_core`
never imports a persona; the dir + cache are passed in.

Why mtime-based cache: editing a prompt and saving must be picked up by the
running bot without a restart. One `stat()` per call invalidates the cache when
the file changes; the cache itself is a micro-optimization for hot paths.
"""

from __future__ import annotations

from pathlib import Path

import structlog

log = structlog.get_logger()

# FULL PATH (str) -> (mtime_ns, content). Keyed by path, NOT by name: callers
# like behavior.content share one cache across many dirs (one per persona), and
# container images give every file the SAME mtime (az acr build tars a fresh
# checkout) — a name-only key + equal mtimes served one persona's prose to
# another (cruel-critic 2026-07-14, GRAVE #1).
PromptCache = dict[str, tuple[int, str]]

# The ENGINE's own prompt dir (fact extraction, consolidation judge, reminder
# delivery): prompts whose audience is a utility model reasoning ABOUT the user,
# never a persona's voice. Persona prose lives under `shared/personas/`.
SHARED_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts_md"


def load_prompt(prompts_dir: Path, name: str, cache: PromptCache) -> str:
    """Read `<prompts_dir>/<name>.md` and return its text content.

    Mtime-aware: re-reads from disk when the file's mtime changes, so editing
    the `.md` and saving picks up immediately without restart. Strips a single
    trailing newline (editors leave one) so concatenation doesn't double up;
    internal newlines are preserved verbatim. Raises ``FileNotFoundError`` with
    the available prompt names if the file is missing — the caller crashes loud
    rather than shipping a malformed LLM call.
    """
    path = prompts_dir / f"{name}.md"
    if not path.exists():
        try:
            available = sorted(p.stem for p in prompts_dir.glob("*.md"))
        except Exception:
            available = []
        raise FileNotFoundError(f"prompt {name!r} not found at {path}. Available: {available[:20]}")
    mtime_ns = path.stat().st_mtime_ns
    cache_key = str(path)
    cached = cache.get(cache_key)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    if text.endswith("\n"):
        text = text[:-1]
    cache[cache_key] = (mtime_ns, text)
    log.info("prompt_loaded", name=name, length=len(text), reload=cached is not None)
    return text


def list_available(prompts_dir: Path) -> list[str]:
    """List all prompt names available on disk under `prompts_dir`."""
    if not prompts_dir.exists():
        return []
    return sorted(p.stem for p in prompts_dir.glob("*.md"))
