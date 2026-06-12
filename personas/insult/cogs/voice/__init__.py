"""Voice cog package.

Re-exports the public surface of ``cog.py`` so that callers importing
from ``insult.cogs.voice`` keep working unchanged after the module was
reorganised into a package.

Future: ``ports.py`` will live here once the ``TranscriptionPort``
(``voice → transcribe`` ratchet item) is opened.
"""

from personas.insult.cogs.voice.cog import (
    _VERSION_TAG_RE,
    VoiceCog,
    build_arbor_tts_payload,
    pick_tts_voice,
    resolve_full_response,
)

__all__ = [
    "_VERSION_TAG_RE",
    "VoiceCog",
    "build_arbor_tts_payload",
    "pick_tts_voice",
    "resolve_full_response",
]
