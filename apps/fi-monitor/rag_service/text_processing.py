"""Text extraction (PDF) + query preprocessing.

Chunking lives in ``fi_core.rag`` now (see ``apps/packages/fi-core``).
Pre-2026-05-19 this module also had its own char-based ``chunk_text``;
that algorithm was distinct from the token-based one in
``backend/services/document/services/chunking_strategy.py``. Both got
unified into ``fi_core.rag.chunk_document`` so fi-monitor and the
backend now share a single chunking implementation.

This module keeps only the PDF/encoding extraction and the Spanish
query preprocessor — both still rag-service-local.
"""

from __future__ import annotations

import io
import re

from fi_core.rag import ChunkConfig, ChunkingStrategy, chunk_document
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes or plain text.

    Args:
        pdf_bytes: PDF file content or plain text as bytes

    Returns:
        Extracted text as string
    """
    # Try PDF extraction first
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        return text.strip()
    except Exception:
        # If PDF parsing fails, assume it's plain text
        try:
            return pdf_bytes.decode("utf-8").strip()
        except Exception:
            # Last resort: try latin-1 encoding
            return pdf_bytes.decode("latin-1").strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into semantic chunks via ``fi_core.rag.chunk_document``.

    Backwards-compatible signature: ``chunk_size`` and ``overlap`` are
    expressed in CHARACTERS (legacy semantic), translated to tokens
    (~4 chars/token average for English/Spanish) before being passed
    to fi-core.

    The pre-2026-05-19 implementation was a hand-rolled paragraph-then-
    sentence splitter. fi-core's PARAGRAPH_AWARE strategy is the same
    idea, more thoroughly tested, and shared across AURITY/Insult so
    upgrades land in one place.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters (soft limit)
        overlap: Overlap between chunks in characters

    Returns:
        List of chunks, paragraph-respecting where possible.
    """
    # Char -> token conversion (avg 4 chars/token for es/en). The
    # 500-char default lands at 125 tokens; the legacy code returned
    # ~500-char chunks, so this preserves the visible behavior of
    # existing call sites without forcing them to learn token units.
    return chunk_document(
        text,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(
            chunk_size=max(chunk_size // 4, 50),
            overlap=max(overlap // 4, 5),
            min_chunk_size=20,
        ),
    )


def preprocess_query(query: str) -> str:
    """Preprocess query to improve matching by removing filler words.

    Args:
        query: Raw user query

    Returns:
        Cleaned query with better semantic signal
    """
    # Remove Spanish question words (que, cual, como, etc.)
    query = re.sub(r'\b(qu\u00e9|cu\u00e1l|c\u00f3mo|d\u00f3nde|por qu\u00e9|cu\u00e1ndo|qui\u00e9n)\b', '', query, flags=re.IGNORECASE)

    # Remove "es la/el" filler (common in Spanish)
    query = re.sub(r'\bes (la|el|los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove "son los/las" filler
    query = re.sub(r'\bson (los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove multiple spaces
    query = re.sub(r'\s+', ' ', query)

    return query.strip()
