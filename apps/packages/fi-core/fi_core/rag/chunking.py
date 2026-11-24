"""Document chunking strategies for RAG.

Splits large documents into smaller chunks for better retrieval.
Three strategies: FIXED_SIZE, SENTENCE_AWARE, PARAGRAPH_AWARE.

Extracted verbatim from free-intelligence (AURITY) — same chunking
logic Bernard already battle-tested for medical PHI, reused here for
Insult's conversational deep_memory. Pure Python, zero dependencies,
Spanish-aware (1.3 tokens/word heuristic).

The embeddings + storage layer differs from AURITY (Azure OpenAI
ada-002 + pgvector vs. on-prem sentence-transformers + HDF5) but the
chunking itself is model-agnostic, so reusing it keeps the two
codebases in sync on that part of the contract.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29 (in free-intelligence/backend/services/document)
Imported: 2026-05-19 (into discord-bot/shared/rag for Insult deep_memory)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum


class ChunkingStrategy(str, Enum):
    """Strategy for splitting documents into chunks."""

    FIXED_SIZE = "fixed_size"  # Fixed token count
    SENTENCE_AWARE = "sentence_aware"  # Respects sentence boundaries
    PARAGRAPH_AWARE = "paragraph_aware"  # Respects paragraph boundaries (best for medical)


class ChunkConfig:
    """Configuration for chunking strategy.

    Validated HERE, at construction, because these numbers arrive from an agent:
    `chunk_document` is an MCP tool and its `chunk_size` / `overlap` are whatever
    the model typed. `chunk_by_fixed_size` advances by `chunk_size - overlap`, so
    an overlap at or above the chunk size is a step of zero or less — the loop
    never terminates AND appends on every pass, so one tool call hangs the stdio
    server and eats the box's memory. A `chunk_size` under 2 does the same thing
    by rounding the words-per-chunk to zero.

    Refusing the config is the fix rather than clamping the step: a caller who
    asked for an impossible window gets told, instead of silently receiving
    chunks with a different overlap than the one they set.

    `count_tokens` replaces the words * 1.3 estimate with the embedder's own
    tokenizer. `max_chunk_size` is a hard ceiling no chunk may pass: an embedder
    drops whatever exceeds its window without a word. With it set, a text that
    fits under it stays in one piece."""

    def __init__(
        self,
        chunk_size: int = 400,  # Target tokens per chunk
        overlap: int = 50,  # Token overlap between chunks
        min_chunk_size: int = 100,  # Minimum chunk size (discard smaller)
        max_chunk_size: int | None = None,
        count_tokens: Callable[[str], int] | None = None,
    ):
        if chunk_size < 2:
            raise ValueError(f"chunk_size must be at least 2 tokens, got {chunk_size!r}")
        if overlap < 0:
            raise ValueError(f"overlap cannot be negative, got {overlap!r}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size}); "
                "an overlap that large means a window that never advances"
            )
        if min_chunk_size < 0:
            raise ValueError(f"min_chunk_size cannot be negative, got {min_chunk_size!r}")
        if max_chunk_size is not None and max_chunk_size < chunk_size:
            raise ValueError(f"max_chunk_size ({max_chunk_size}) cannot be under chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.count_tokens = count_tokens or estimate_tokens


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (words * 1.3 for Spanish).

    More accurate than word count, faster than actual tokenization.
    """
    words = len(text.split())
    return int(words * 1.3)  # Spanish: ~1.3 tokens per word on average


def chunk_by_fixed_size(text: str, config: ChunkConfig) -> list[str]:
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
        chunk_words = words[i : i + words_per_chunk]
        chunk_text = " ".join(chunk_words)

        if config.count_tokens(chunk_text) >= config.min_chunk_size:
            chunks.append(chunk_text)
        elif chunks:
            # The TAIL, too short to stand alone. Dropping it deleted the end of
            # the document in silence: measured at defaults, a 330-word text came
            # back as one chunk covering 307 words, with w307..w329 present in NO
            # chunk and no signal that anything was missing. The end of a document
            # is where conclusions and the most recent entries live, so it is the
            # worst part to lose.
            #
            # `min_chunk_size` means "no tiny chunks", not "discard text", so the
            # remainder joins the previous chunk. With no previous chunk the whole
            # document is simply too short — that stays a drop, and `RagStore`
            # turns the resulting zero into `NothingToIndex` rather than a silent
            # success.
            tail = chunk_words[words_overlap:]
            if tail:
                chunks[-1] = chunks[-1] + " " + " ".join(tail)

        # Move forward with overlap
        i += words_per_chunk - words_overlap

    return chunks


def chunk_by_sentences(text: str, config: ChunkConfig) -> list[str]:
    """Split text into chunks respecting sentence boundaries.

    Better than fixed-size: keeps sentences intact.
    Good for general documents.
    """
    sentences = _SENTENCE_END.split(text)

    chunks = []
    current_chunk = []
    current_tokens = 0
    carried = 0

    for sentence in sentences:
        sentence_tokens = config.count_tokens(sentence)

        # If adding this sentence exceeds chunk_size, start new chunk
        overflows = current_tokens + sentence_tokens > config.chunk_size
        if overflows and current_chunk and current_tokens >= config.min_chunk_size:
            chunks.append(" ".join(current_chunk))
            # Keep overlap (last few sentences)
            overlap_sentences = []
            overlap_tokens = 0
            for s in reversed(current_chunk):
                s_tokens = config.count_tokens(s)
                if overlap_tokens + s_tokens <= config.overlap:
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens
                else:
                    break
            current_chunk = overlap_sentences
            current_tokens = overlap_tokens
            carried = len(current_chunk)

        current_chunk.append(sentence)
        current_tokens += sentence_tokens

    # Add final chunk
    if current_chunk:
        _close_tail(chunks, current_chunk, carried, separator=" ", config=config)

    return chunks


def chunk_by_paragraphs(text: str, config: ChunkConfig) -> list[str]:
    """Split text into chunks respecting paragraph boundaries.

    BEST for medical documents: preserves clinical context.
    Paragraphs in medical texts often represent complete concepts.
    """
    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = []
    current_tokens = 0
    carried = 0

    for paragraph in paragraphs:
        para_tokens = config.count_tokens(paragraph)

        # If paragraph alone exceeds chunk_size, split it by sentences
        if para_tokens > config.chunk_size * 1.5:
            # Flush current chunk first; a lone heading opens the paragraph it introduces
            if current_chunk and current_tokens < config.min_chunk_size:
                paragraph = "\n\n".join([*current_chunk[carried:], paragraph])
            elif current_chunk:
                chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0
            carried = 0

            # Split large paragraph by sentences
            para_chunks = chunk_by_sentences(paragraph, config)
            chunks.extend(para_chunks)
            continue

        # If adding this paragraph exceeds chunk_size, start new chunk
        overflows = current_tokens + para_tokens > config.chunk_size
        if overflows and current_chunk and current_tokens >= config.min_chunk_size:
            chunks.append("\n\n".join(current_chunk))
            # Keep overlap (last paragraph if small enough)
            if current_chunk and config.count_tokens(current_chunk[-1]) <= config.overlap:
                current_chunk = [current_chunk[-1]]
                current_tokens = config.count_tokens(current_chunk[-1])
            else:
                current_chunk = []
                current_tokens = 0
            carried = len(current_chunk)

        current_chunk.append(paragraph)
        current_tokens += para_tokens

    # Add final chunk
    if current_chunk:
        _close_tail(chunks, current_chunk, carried, separator="\n\n", config=config)

    return chunks


def _close_tail(chunks: list[str], tail: list[str], carried: int, *, separator: str, config: ChunkConfig) -> None:
    """Close the document's last piece: its own chunk, or joined to the previous when under the minimum.

    The first `carried` parts are overlap the previous chunk already holds. A
    whole document under the minimum still yields nothing.
    """
    text = separator.join(tail)
    if config.count_tokens(text) >= config.min_chunk_size:
        chunks.append(text)
    elif chunks and tail[carried:]:
        chunks[-1] = separator.join([chunks[-1], *tail[carried:]])


def _split_to_fit(text: str, config: ChunkConfig) -> list[str]:
    """Halve `text` at the sentence (else word, else character) nearest its middle until every piece fits."""
    if config.max_chunk_size is None or config.count_tokens(text) <= config.max_chunk_size or len(text) < 2:
        return [text]
    middle = len(text) // 2
    cuts = [m.end() for m in _SENTENCE_END.finditer(text)] or [m.end() for m in re.finditer(r"\s+", text)]
    cut = min((c for c in cuts if 0 < c < len(text)), key=lambda c: abs(c - middle), default=middle)
    halves = (text[:cut].strip(), text[cut:].strip())
    return [piece for half in halves if half for piece in _split_to_fit(half, config)]


def chunk_document(
    text: str, strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH_AWARE, config: ChunkConfig | None = None
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

    tokens = config.count_tokens(text)
    if config.max_chunk_size is not None and config.min_chunk_size <= tokens <= config.max_chunk_size:
        return [text.strip()]

    # Route to appropriate strategy
    chunkers: dict[ChunkingStrategy, Callable[[str, ChunkConfig], list[str]]] = {
        ChunkingStrategy.FIXED_SIZE: chunk_by_fixed_size,
        ChunkingStrategy.SENTENCE_AWARE: chunk_by_sentences,
        ChunkingStrategy.PARAGRAPH_AWARE: chunk_by_paragraphs,
    }

    chunker = chunkers.get(strategy, chunk_by_paragraphs)
    return [piece for chunk in chunker(text, config) for piece in _split_to_fit(chunk, config)]


__all__ = [
    "ChunkConfig",
    "ChunkingStrategy",
    "chunk_document",
    "estimate_tokens",
]
