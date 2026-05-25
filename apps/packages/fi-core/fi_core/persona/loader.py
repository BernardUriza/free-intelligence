"""mtime-aware persona loader — hot-reload a system prompt from a file.

Every runner with a file-based system prompt needs the same trick: read the
persona file once, cache it, and reload only when the file's mtime changes — so
editing the persona in a running container updates the prompt on the NEXT turn,
no redeploy. Extracted from the per-bot loaders (Insult's prompts_loader, ALICE's
persona_loader) so every runner shares one implementation.

Zero-dep and transport-agnostic: the path is required (no app-specific settings
default), logging goes through stdlib ``logging`` (no structlog), and it lives in
its own module so importing it does NOT pull the persona package's ``mcp`` extra::

    from fi_core.persona.loader import PersonaLoader
    persona = PersonaLoader("alice/persona.md")
    system_prompt = persona.load()  # re-reads only if the file changed

The loader returns the raw text, not a parsed structure — a persona is one
document. For multi-section / multi-variant prompts, use the YAML preset
machinery in :mod:`fi_core.cognitive` instead.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

_log = logging.getLogger(__name__)


class PersonaLoader:
    """Caches a persona file's text, reloading it when the file mtime changes."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._lock = threading.Lock()
        self._cached_text: str = ""
        self._cached_mtime: float | None = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> str:
        """Return the persona text, refreshing the cache if the file changed.

        Thread-safe: the stat-check, read, and cache update happen under a lock so
        a concurrent editor can't make a caller observe a half-loaded buffer.
        Raises :class:`FileNotFoundError` if the persona file is missing.
        """
        try:
            current_mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            _log.error("persona file missing: %s", self._path)
            raise

        with self._lock:
            if current_mtime != self._cached_mtime:
                self._cached_text = self._path.read_text(encoding="utf-8")
                self._cached_mtime = current_mtime
                _log.info(
                    "persona loaded: path=%s chars=%d mtime=%s",
                    self._path,
                    len(self._cached_text),
                    current_mtime,
                )
            return self._cached_text
