#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Corpus Operations

Functions for appending and reading data from HDF5 corpus.
Demonstrates end-to-end flow: config → logger → corpus storage.

FI-DATA-OPS (Test/Demo)
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import h5py
import numpy as np


def append_interaction(
    corpus_path: str,
    session_id: str,
    prompt: str,
    response: str,
    model: str,
    tokens: int,
    timestamp: Optional[str] = None,
) -> str:
    """
    Append interaction to corpus.

    Args:
        corpus_path: Path to HDF5 corpus
        session_id: Session identifier
        prompt: User prompt
        response: Model response
        model: Model name used
        tokens: Total tokens used
        timestamp: ISO timestamp (auto-generated if None)

    Returns:
        interaction_id (UUID)

    Raises:
        AppendOnlyViolation: If operation violates append-only policy

    Examples:
        >>> interaction_id = append_interaction(
        ...     "storage/corpus.h5",
        ...     "session_20251024_235000",
        ...     "What is Free Intelligence?",
        ...     "Free Intelligence is a local AI memory system...",
        ...     "claude-3-5-sonnet-20241022",
        ...     150
        ... )
    """
    from fi_common.logging.logger import get_logger

    from backend.append_only_policy import AppendOnlyPolicy

    logger = get_logger()
    interaction_id = str(uuid.uuid4())

    if timestamp is None:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Mexico_City")
        timestamp = datetime.now(tz).isoformat()

    try:
        with AppendOnlyPolicy(corpus_path), h5py.File(corpus_path, "a") as f:
            interactions = f["interactions"]

            # Current size
            current_size = interactions["session_id"].shape[0]  # type: ignore[index]
            new_size = current_size + 1

            # Resize all datasets
            for dataset_name in interactions.keys():  # type: ignore[attr-defined]
                interactions[dataset_name].resize((new_size,))  # type: ignore[attr-defined]

            # Append data
            interactions["session_id"][current_size] = session_id  # type: ignore[index]
            interactions["interaction_id"][current_size] = interaction_id  # type: ignore[index]
            interactions["timestamp"][current_size] = timestamp  # type: ignore[index]
            interactions["prompt"][current_size] = prompt  # type: ignore[index]
            interactions["response"][current_size] = response  # type: ignore[index]
            interactions["model"][current_size] = model  # type: ignore[index]
            interactions["tokens"][current_size] = tokens  # type: ignore[index]

        logger.info(
            "INTERACTION_APPENDED",
            interaction_id=interaction_id,
            session_id=session_id,
            tokens=tokens,
            model=model,
        )

        return interaction_id

    except Exception as e:
        logger.error("INTERACTION_APPEND_FAILED", error=str(e))
        raise


def append_embedding(
    corpus_path: str, interaction_id: str, vector: np.ndarray, model: str = "all-MiniLM-L6-v2"
) -> bool:
    """
    Append embedding vector to corpus.

    Args:
        corpus_path: Path to HDF5 corpus
        interaction_id: Reference to interaction
        vector: Embedding vector (768-dim)
        model: Embedding model name

    Returns:
        True if successful

    Raises:
        AppendOnlyViolation: If operation violates append-only policy

    Examples:
        >>> vector = np.random.rand(768).astype(np.float32)
        >>> append_embedding("storage/corpus.h5", interaction_id, vector)
        True
    """
    from fi_common.logging.logger import get_logger

    from backend.append_only_policy import AppendOnlyPolicy

    logger = get_logger()

    if vector.shape != (768,):
        raise ValueError(f"Vector must be 768-dim, got {vector.shape}")

    try:
        with AppendOnlyPolicy(corpus_path), h5py.File(corpus_path, "a") as f:
            embeddings = f["embeddings"]

            # Current size
            current_size = embeddings["interaction_id"].shape[0]  # type: ignore[attr-defined]
            new_size = current_size + 1

            # Resize datasets
            embeddings["interaction_id"].resize((new_size,))  # type: ignore[index]
            embeddings["vector"].resize((new_size, 768))  # type: ignore[index]
            embeddings["model"].resize((new_size,))  # type: ignore[index]

            # Append data
            embeddings["interaction_id"][current_size] = interaction_id  # type: ignore[index]
            embeddings["vector"][current_size] = vector  # type: ignore[index]
            embeddings["model"][current_size] = model  # type: ignore[index]

        logger.info(
            "EMBEDDING_APPENDED",
            interaction_id=interaction_id,
            model=model,
            vector_dim=vector.shape[0],
        )

        return True

    except Exception as e:
        logger.error("EMBEDDING_APPEND_FAILED", error=str(e))
        return False


def append_interaction_with_embedding(
    corpus_path: str,
    session_id: str,
    prompt: str,
    response: str,
    model: str,
    tokens: int,
    timestamp: Optional[str] = None,
    auto_embed: bool = True,
) -> str:
    """
    Append interaction to corpus WITH automatic embedding generation.

    This is the END-TO-END function that:
    1. Appends interaction to /interactions/
    2. Generates embedding using LLM router
    3. Appends embedding to /embeddings/
    4. Logs everything to audit_logs

    Args:
        corpus_path: Path to HDF5 corpus
        session_id: Session identifier
        prompt: User prompt
        response: Model response
        model: Model name used
        tokens: Total tokens used
        timestamp: ISO timestamp (auto-generated if None)
        auto_embed: Whether to automatically generate embedding (default: True)

    Returns:
        interaction_id (UUID)

    Examples:
        >>> interaction_id = append_interaction_with_embedding(
        ...     "storage/corpus.h5",
        ...     "session_20251028_010000",
        ...     "What is Free Intelligence?",
        ...     "Free Intelligence is a local AI memory system...",
        ...     "claude-3-5-sonnet-20241022",
        ...     150
        ... )
    """
    from fi_common.logging.logger import get_logger

    from backend.llm_router import llm_embed, pad_embedding_to_768

    logger = get_logger()

    # Step 1: Append interaction
    logger.info("INTERACTION_WITH_EMBEDDING_STARTED", session_id=session_id, auto_embed=auto_embed)

    interaction_id = append_interaction(
        corpus_path=corpus_path,
        session_id=session_id,
        prompt=prompt,
        response=response,
        model=model,
        tokens=tokens,
        timestamp=timestamp,
    )

    # Step 2: Generate and append embedding (if enabled)
    if auto_embed:
        try:
            # Combine prompt and response for embedding
            text_to_embed = f"{prompt}\n\n{response}"

            logger.info(
                "EMBEDDING_GENERATION_STARTED",
                interaction_id=interaction_id,
                text_length=len(text_to_embed),
            )

            # Use LLM router to generate embedding
            # Will use policy-configured provider or fall back to sentence-transformers
            embedding_vector = llm_embed(text_to_embed)

            # Pad to 768 dimensions if needed (shared utility)
            embedding_vector = pad_embedding_to_768(embedding_vector)

            # Append to corpus
            append_embedding(
                corpus_path=corpus_path,
                interaction_id=interaction_id,
                vector=embedding_vector,
                model="all-MiniLM-L6-v2",  # Could be dynamic based on provider
            )

            logger.info("INTERACTION_WITH_EMBEDDING_COMPLETED", interaction_id=interaction_id)

        except Exception as e:
            logger.error("EMBEDDING_GENERATION_FAILED", interaction_id=interaction_id, error=str(e))
            # Don't fail the whole operation if embedding fails
            # The interaction is already saved

    return interaction_id


def get_corpus_stats(corpus_path: str) -> dict:
    """
    Get corpus statistics.

    Args:
        corpus_path: Path to HDF5 corpus

    Returns:
        Dictionary with stats

    Examples:
        >>> stats = get_corpus_stats("storage/corpus.h5")
        >>> print(stats["interactions_count"])
    """
    from fi_common.logging.logger import get_logger

    logger = get_logger()

    try:
        with h5py.File(corpus_path, "r") as f:
            interactions_count = f["interactions"]["session_id"].shape[0]  # type: ignore[index]
            embeddings_count = f["embeddings"]["interaction_id"].shape[0]  # type: ignore[index]

            # Get file size
            file_size = Path(corpus_path).stat().st_size

            # Get metadata
            metadata = dict(f["metadata"].attrs)  # type: ignore[attr-defined]

            stats = {
                "interactions_count": interactions_count,
                "embeddings_count": embeddings_count,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "created_at": metadata.get("created_at"),
                "version": metadata.get("version"),
                "schema_version": metadata.get("schema_version"),
            }

            logger.info("STATS_SNAPSHOT_COMPUTED", **stats)

            return stats

    except Exception as e:
        logger.error("CORPUS_STATS_FAILED", error=str(e))
        return {}


def read_interactions(corpus_path: str, limit: int = 10) -> list[dict]:
    """
    Read recent interactions from corpus.

    Args:
        corpus_path: Path to HDF5 corpus
        limit: Number of interactions to read

    Returns:
        List of interaction dictionaries

    Examples:
        >>> interactions = read_interactions("storage/corpus.h5", limit=5)
        >>> for interaction in interactions:
        ...     print(interaction["prompt"])
    """
    try:
        with h5py.File(corpus_path, "r") as f:
            interactions_group = f["interactions"]
            total = interactions_group["session_id"].shape[0]  # type: ignore[index]

            if total == 0:
                return []

            # Read last N interactions
            start = max(0, total - limit)
            end = total

            results = []
            for i in range(start, end):
                interaction = {
                    "session_id": interactions_group["session_id"][i].decode("utf-8"),  # type: ignore[index]
                    "interaction_id": interactions_group["interaction_id"][i].decode("utf-8"),  # type: ignore[attr-defined]
                    "timestamp": interactions_group["timestamp"][i].decode("utf-8"),  # type: ignore[index]
                    "prompt": interactions_group["prompt"][i].decode("utf-8"),  # type: ignore[index]
                    "response": interactions_group["response"][i].decode("utf-8"),  # type: ignore[index]
                    "model": interactions_group["model"][i].decode("utf-8"),  # type: ignore[attr-defined]
                    "tokens": int(interactions_group["tokens"][i]),  # type: ignore[index]
                }
                results.append(interaction)

            return results

    except Exception as e:
        from fi_common.logging.logger import get_logger

        logger = get_logger()
        logger.error("INTERACTIONS_READ_FAILED", error=str(e))
        return []


if __name__ == "__main__":
    # Demo
    from backend.config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    print("📊 Corpus Statistics:")
    stats = get_corpus_stats(corpus_path)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n📖 Recent Interactions:")
    interactions = read_interactions(corpus_path, limit=5)
    for i, interaction in enumerate(interactions, 1):
        print(f"\n  [{i}] {interaction['timestamp']}")
        print(f"      Prompt: {interaction['prompt'][:60]}...")
        print(f"      Response: {interaction['response'][:60]}...")
        print(f"      Model: {interaction['model']}, Tokens: {interaction['tokens']}")
