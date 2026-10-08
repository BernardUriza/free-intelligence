"""Persona DNA resolution + loading — the anti-path-traversal boundary.

A `persona_id` arrives from the wire. It selects which `.md` becomes a session's
system prompt, so it is an UNTRUSTED path component: the allowlist regex is the
only thing between a caller and `../../etc/passwd`. Kept in its own module so
that boundary is one obvious file, not a helper buried mid-monolith.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from persona_runner.core import config

log = structlog.get_logger()


def resolve_persona_path(persona_id: str | None) -> Path:
    """Map a persona_id to its DNA file, defaulting to the base persona.

    Returns PERSONA_PATH when persona_id is None, fails the allowlist (anti
    path-traversal), or the sibling file is missing — logging the unknown case so
    a typo'd id is visible instead of silently impersonating the default persona.
    """
    if not persona_id:
        return config.PERSONA_PATH
    if not config.PERSONA_ID_RE.match(persona_id):
        log.warning("agent_runner_persona_invalid_id", persona_id=persona_id)
        return config.PERSONA_PATH
    candidate = config.PERSONAS_DIR / f"{persona_id}.md"
    if not candidate.exists():
        log.warning("agent_runner_persona_unknown", persona_id=persona_id, path=str(candidate))
        return config.PERSONA_PATH
    return candidate


def load_persona(persona_id: str | None = None) -> str:
    """Read the persona markdown from disk — on new-session creation only.

    Each long-lived ClaudeSDKClient gets the persona inlined as its system_prompt
    at construction time; the SDK then caches it for that client's lifetime.
    Re-reading from disk is cheap and lets an `mtime` update take effect on the
    NEXT new session (edit the .md, no redeploy).
    """
    path = resolve_persona_path(persona_id)
    if not path.exists():
        log.error("agent_runner_persona_missing", path=str(path))
        return ""
    return path.read_text(encoding="utf-8")
