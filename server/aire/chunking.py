"""How a document becomes searchable pieces — text in, chunks out, no database.

Its own module because it is its own job, the way fi-core separates `rag/chunking`
from its store (Art. 6): the corpus decides where pieces live, this decides what a
piece IS, and the two change for different reasons.

Paragraph-first, because a hit is read by a MODEL: a chunk cut mid-sentence
retrieves fine and then hands back something the model has to guess the end of.
Splitting on blank lines keeps whole thoughts together; a paragraph longer than the
budget rides alone rather than being sliced.
"""

from __future__ import annotations

CHUNK_CHARS = 1500


def chunk(text: str, budget: int = CHUNK_CHARS) -> list[str]:
    """The document as chunks of about `budget` characters, in order."""
    out: list[str] = []
    current = ""
    for para in (p.strip() for p in text.split("\n\n")):
        if not para:
            continue
        if current and len(current) + len(para) + 2 > budget:
            out.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        out.append(current)
    return out
