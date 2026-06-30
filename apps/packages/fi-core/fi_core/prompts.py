"""Canonical prompt loader — LLM-facing prompts live in content files, not source.

Per the playbook P0 ``prompts-as-content-not-code``: a persona/system prompt is
CONTENT humans iterate on, not code. It belongs in an external ``.md``/``.txt``
file loaded at runtime, NEVER as an inline Python string. This is the single
canonical loader for the WHOLE fi stack — it lives in fi-core (the lowest shared
layer, dep-free), so fi-core, fi-runner (which re-exports it) and every consumer
(og118, alice, ferboli, the next shell) reuse ONE loader instead of each rolling
its own.

The loader is mtime-aware: call ``load_prompt(path)`` *inside the function that
uses the prompt* (e.g. per turn), and editing the file is picked up on the next
call without a restart. The parsed content is cached keyed on ``(path, mtime)``,
so an unchanged file costs only a ``stat``.
"""

from __future__ import annotations

from pathlib import Path

_cache: dict[tuple[str, float], str] = {}


def load_prompt(path: str | Path) -> str:
    """Return the text of a prompt file, hot-reloading when its mtime changes.

    ``path`` is the prompt content file (``.md``/``.txt``). The returned string is
    the file's text with trailing whitespace stripped. Raises ``FileNotFoundError``
    if the file is absent — a missing prompt is a hard failure, never a silent
    empty system prompt.
    """
    resolved = Path(path).expanduser().resolve()
    mtime = resolved.stat().st_mtime
    key = (str(resolved), mtime)
    cached = _cache.get(key)
    if cached is None:
        cached = resolved.read_text(encoding="utf-8").rstrip()
        _cache[key] = cached
    return cached


__all__ = ["load_prompt"]
