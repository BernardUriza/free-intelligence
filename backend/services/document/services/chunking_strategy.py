"""Document chunking strategies for RAG.

Splits large documents into smaller chunks for better retrieval.
Medical documents need special handling to preserve clinical context.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Document Repository Implementation
"""

from __future__ import annotations

from enum import Enum
from typing import Callable


class ChunkingStrategy(str, Enum):
    """Strategy for splitting documents into chunks."""

    FIXED_SIZE = "fixed_size"           # Fixed token count
    SENTENCE_AWARE = "sentence_aware"   # Respects sentence boundaries
    PARAGRAPH_AWARE = "paragraph_aware" # Respects paragraph boundaries (best for medical)


class ChunkConfig:
    """Configuration for chunking strategy."""

    def __init__(
        self,
        chunk_size: int = 400,  # Target tokens per chunk
        overlap: int = 50,       # Token overlap between chunks
        min_chunk_size: int = 100  # Minimum chunk size (discard smaller)
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (words * 1.3 for Spanish).

    More accurate than word count, faster than actual tokenization.
    """
    words = len(text.split())
    return int(words * 1.3)  # Spanish: ~1.3 tokens per word on average


def chunk_by_fixed_size(
    text: str,
    config: ChunkConfig
) -> list[str]:
    """Split text into fixed-size chunks with overlap.

    Simple but loses context at boundaries. Use only if other strategies fail.
    """
    words = text.split()
    chunks = []

    # Convert token sizes to word counts (approximate)
    words_per_chunk = int(config.chunk_size / 1.3)
    words_overlap = int(config.overlap / 1.3)

    i = 0
    while i < len(words):
        chunk_words = words[i:i + words_per_chunk]
        chunk_text = " ".join(chunk_words)

        if estimate_tokens(chunk_text) >= config.min_chunk_size:
            chunks.append(chunk_text)

        # Move forward with overlap
        i += words_per_chunk - words_overlap

    return chunks


def chunk_by_sentences(
    text: str,
    config: ChunkConfig
) -> list[str]:
    """Split text into chunks respecting sentence boundaries.

    Better than fixed-size: keeps sentences intact.
    Good for general documents.
    """
    # Simple sentence splitting (Spanish-aware)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)

        # If adding this sentence exceeds chunk_size, start new chunk
        if current_tokens + sentence_tokens > config.chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Keep overlap (last few sentences)
            overlap_sentences = []
            overlap_tokens = 0
            for s in reversed(current_chunk):
                s_tokens = estimate_tokens(s)
                if overlap_tokens + s_tokens <= config.overlap:
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens
                else:
                    break
            current_chunk = overlap_sentences
            current_tokens = overlap_tokens

        current_chunk.append(sentence)
        current_tokens += sentence_tokens

    # Add final chunk
    if current_chunk:
        final_text = " ".join(current_chunk)
        if estimate_tokens(final_text) >= config.min_chunk_size:
            chunks.append(final_text)

    return chunks


def chunk_by_paragraphs(
    text: str,
    config: ChunkConfig
) -> list[str]:
    """Split text into chunks respecting paragraph boundaries.

    BEST for medical documents: preserves clinical context.
    Paragraphs in medical texts often represent complete concepts.
    """
    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = []
    current_tokens = 0

    for paragraph in paragraphs:
        para_tokens = estimate_tokens(paragraph)

        # If paragraph alone exceeds chunk_size, split it by sentences
        if para_tokens > config.chunk_size * 1.5:
            # Flush current chunk first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # Split large paragraph by sentences
            para_chunks = chunk_by_sentences(paragraph, config)
            chunks.extend(para_chunks)
            continue

        # If adding this paragraph exceeds chunk_size, start new chunk
        if current_tokens + para_tokens > config.chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            # Keep overlap (last paragraph if small enough)
            if current_chunk and estimate_tokens(current_chunk[-1]) <= config.overlap:
                current_chunk = [current_chunk[-1]]
                current_tokens = estimate_tokens(current_chunk[-1])
            else:
                current_chunk = []
                current_tokens = 0

        current_chunk.append(paragraph)
        current_tokens += para_tokens

    # Add final chunk
    if current_chunk:
        final_text = "\n\n".join(current_chunk)
        if estimate_tokens(final_text) >= config.min_chunk_size:
            chunks.append(final_text)

    return chunks


def chunk_document(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH_AWARE,
    config: ChunkConfig | None = None
) -> list[str]:
    """Split document into chunks using specified strategy.

    Args:
        text: Full document text
        strategy: Chunking strategy to use
        config: Optional chunking configuration

    Returns:
        List of text chunks

    Medical Context:
        Paragraph-aware is BEST for medical documents because:
        - Preserves clinical context (symptoms, diagnosis, treatment)
        - Keeps drug interactions in same chunk
        - Maintains diagnostic criteria together
    """
    if config is None:
        config = ChunkConfig()

    # Route to appropriate strategy
    chunkers: dict[ChunkingStrategy, Callable[[str, ChunkConfig], list[str]]] = {
        ChunkingStrategy.FIXED_SIZE: chunk_by_fixed_size,
        ChunkingStrategy.SENTENCE_AWARE: chunk_by_sentences,
        ChunkingStrategy.PARAGRAPH_AWARE: chunk_by_paragraphs,
    }

    chunker = chunkers.get(strategy, chunk_by_paragraphs)
    return chunker(text, config)


__all__ = [
    "ChunkingStrategy",
    "ChunkConfig",
    "chunk_document",
    "estimate_tokens",
]
