"""Per-persona guidance content loader — the seam between ENGINE and VOICE.

The behavior engine (presets classifier, flows pipeline, vulnerability scoring)
is persona-agnostic: it reads the USER's state, never a persona's identity. What
each persona DOES with a selected mode is content, written in that persona's
voice, living under ``shared/personas/guidance/<persona_id>/<kind>/<name>.md``.

Any robot opts in by adding files there; a persona with no guidance content gets
an empty string back (mode still selected, no voice-specific prose) — the engine
never crashes because a persona hasn't written its voice yet.

Mtime-aware via ``persona_core.prompts``: editing a .md is picked up on the
next request, no redeploy.
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog

from persona_core.prompts import PromptCache
from persona_core.prompts import load_prompt as _load_prompt

log = structlog.get_logger()

# Repo-adjacent by default (works in both container images: WORKDIR /app with
# persona_core/ and shared/ side by side). KHIMERAS_GUIDANCE_ROOT overrides
# for the day persona_core ships as an installed package and "adjacent
# shared/" stops existing (cruel-critic 2026-07-14, IMPORTANTE #2).
_GUIDANCE_ROOT = Path(
    os.environ.get(
        "KHIMERAS_GUIDANCE_ROOT",
        str(Path(__file__).resolve().parent.parent.parent / "shared" / "personas" / "guidance"),
    )
)

_CACHE: PromptCache = {}


def guidance_dir(persona_id: str, kind: str) -> Path:
    """Directory holding a persona's guidance content for one engine (presets/flows)."""
    return _GUIDANCE_ROOT / persona_id / kind


def load_guidance(persona_id: str, kind: str, name: str) -> str:
    """Read ``shared/personas/guidance/<persona_id>/<kind>/<name>.md``.

    Returns "" when the persona has no content for that name — a persona that
    hasn't written its voice for a mode simply adds nothing to the prompt.
    """
    try:
        return _load_prompt(guidance_dir(persona_id, kind), name, _CACHE)
    except FileNotFoundError:
        log.debug("guidance_content_absent", persona_id=persona_id, kind=kind, name=name)
        return ""


def clear_guidance_cache() -> None:
    """Empty the cache — tests call this when mtime granularity is coarse."""
    _CACHE.clear()
