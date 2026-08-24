"""How a document becomes searchable — chunked, and folded for matching. No database.

Its own module because it is its own job, the way fi-core separates `rag/chunking`
from its store (Art. 6): the corpus decides where pieces live, this decides what a
piece IS, and the two change for different reasons.

Paragraph-first, because a hit is read by a MODEL: a chunk cut mid-sentence
retrieves fine and then hands back something the model has to guess the end of.
Splitting on blank lines keeps whole thoughts together; a paragraph longer than the
budget rides alone rather than being sliced.
"""

from __future__ import annotations

import unicodedata

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


def fold(text: str) -> str:
    """The text as it is MATCHED against, with its accents removed.

    Postgres's `spanish` configuration stems and drops stopwords, but it does not
    fold diacritics without the `unaccent` extension — so `telemetría` and
    `telemetria` are two different words to it. Measured on the live gate the hour
    this shipped: a model searching "telemetría" missed a document that said
    "telemetria" and had to retry twice with narrower queries before it found it.
    In Spanish that is the single most common way a search quietly fails, and the
    user pays for it in retries.

    Folding in Python instead of installing `unaccent` keeps this working on any
    Postgres, with no extension to enable and no superuser to ask. The ORIGINAL
    text is what gets stored and returned; only the matching copy is folded.
    """
    return "".join(ch for ch in unicodedata.normalize("NFD", text)
                   if unicodedata.category(ch) != "Mn")
