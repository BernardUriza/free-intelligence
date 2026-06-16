"""Generic, persona-neutral prompt loader — mtime-aware reads from a `.md` dir.

Why this lives in `khimeras_shared`: loading prompts from `.md` files (so the
operator edits content in git, not Python string constants, and the running bot
hot-reloads on save) is a CAPABILITY both personas want — not Insult-specific. It
is parameterized by the prompts directory, so each persona binds its own dir in a
thin wrapper (e.g. `personas/insult/core/prompts_loader.py`). `khimeras_shared`
never imports a persona; the dir + cache are passed in.

Why mtime-based cache: editing a prompt and saving must be picked up by the
running bot without a restart. One `stat()` per call invalidates the cache when
the file changes; the cache itself is a micro-optimization for hot paths.
"""

from __future__ import annotations

from pathlib import Path

import structlog

log = structlog.get_logger()

# name -> (mtime_ns, content)
PromptCache = dict[str, tuple[int, str]]


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
    cached = cache.get(name)
    if cached is not None and cached[0] == mtime_ns:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    if text.endswith("\n"):
        text = text[:-1]
    cache[name] = (mtime_ns, text)
    log.info("prompt_loaded", name=name, length=len(text), reload=cached is not None)
    return text


def list_available(prompts_dir: Path) -> list[str]:
    """List all prompt names available on disk under `prompts_dir`."""
    if not prompts_dir.exists():
        return []
    return sorted(p.stem for p in prompts_dir.glob("*.md"))
