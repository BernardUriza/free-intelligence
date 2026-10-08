"""Text formatting primitives shared between Insult and ALICE."""

from shared.text.chunking import (
    DISCORD_MAX_CHARS,
    chunk_hard,
    chunk_paragraph_aware,
)
from shared.text.delimiters import MESSAGE_DELIMITER, split_response

__all__ = [
    "DISCORD_MAX_CHARS",
    "MESSAGE_DELIMITER",
    "chunk_hard",
    "chunk_paragraph_aware",
    "split_response",
]
