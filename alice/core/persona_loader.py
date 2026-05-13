"""mtime-aware persona loader for ALICE.

Same idea as Insult's `prompts_loader`: reads `alice/persona.md` on
disk, caches it, reloads on mtime change. This means editing the
persona file in a running container updates ALICE's system prompt on
the NEXT message — no redeploy needed.

The loader returns the raw text, not a parsed structure. ALICE's
persona is one document, not a multi-section template, so there's no
need for the YAML preset machinery of free-intelligence here. If we
ever ship multiple ALICE variants (`alice-clinical`, `alice-relational`),
we'd switch to YAML at that point.
"""

from __future__ import annotations

import threading
from pathlib import Path

import structlog

from alice.config import settings

log = structlog.get_logger()


class PersonaLoader:
    """Caches the persona file, reloads it when the file mtime changes."""

    def __init__(self, path: str | None = None):
        self._path = Path(path or settings.persona_path)
        self._lock = threading.Lock()
        self._cached_text: str = ""
        self._cached_mtime: float = 0.0

    def load(self) -> str:
        """Return persona text, refreshing the cache if the file changed.

        Thread-safe: stat + read happen under a lock so a concurrent
        editor can't observe a half-loaded buffer.
        """
        try:
            current_mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            log.error("alice_persona_missing", path=str(self._path))
            raise

        with self._lock:
            if current_mtime != self._cached_mtime:
                self._cached_text = self._path.read_text(encoding="utf-8")
                self._cached_mtime = current_mtime
                log.info(
                    "alice_persona_loaded",
                    path=str(self._path),
                    chars=len(self._cached_text),
                    mtime=current_mtime,
                )
            return self._cached_text


# Module-level singleton, lazy-instantiated.
_loader: PersonaLoader | None = None


def get_persona_loader() -> PersonaLoader:
    global _loader
    if _loader is None:
        _loader = PersonaLoader()
    return _loader
