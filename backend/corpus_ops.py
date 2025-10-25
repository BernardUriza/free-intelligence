#!/usr/bin/env python3
"""
Free Intelligence - Corpus Operations

Functions for appending and reading data from HDF5 corpus.
Demonstrates end-to-end flow: config → logger → corpus storage.

FI-DATA-OPS (Test/Demo)
"""

import h5py
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid


def append_interaction(
    corpus_path: str,
    session_id: str,
    prompt: str,
    response: str,
    model: str,
    tokens: int,
    timestamp: Optional[str] = None
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
    from logger import get_logger

    logger = get_logger()
    interaction_id = str(uuid.uuid4())

    if timestamp is None:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Mexico_City")
        timestamp = datetime.now(tz).isoformat()

    try:
        with h5py.File(corpus_path, 'a') as f:
            interactions = f["interactions"]

            # Current size
            current_size = interactions["session_id"].shape[0]
            new_size = current_size + 1

            # Resize all datasets
            for dataset_name in interactions.keys():
                interactions[dataset_name].resize((new_size,))

            # Append data
            interactions["session_id"][current_size] = session_id
            interactions["interaction_id"][current_size] = interaction_id
            interactions["timestamp"][current_size] = timestamp
            interactions["prompt"][current_size] = prompt
            interactions["response"][current_size] = response
            interactions["model"][current_size] = model
            interactions["tokens"][current_size] = tokens

        logger.info(
            "interaction_appended",
            interaction_id=interaction_id,
            session_id=session_id,
            tokens=tokens,
            model=model
        )

        return interaction_id

    except Exception as e:
        logger.error("interaction_append_failed", error=str(e), session_id=session_id)
        raise


def append_embedding(
    corpus_path: str,
    interaction_id: str,
    vector: np.ndarray,
    model: str = "all-MiniLM-L6-v2"
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

    Examples:
        >>> vector = np.random.rand(768).astype(np.float32)
        >>> append_embedding("storage/corpus.h5", interaction_id, vector)
        True
    """
    from logger import get_logger

    logger = get_logger()

    if vector.shape != (768,):
        raise ValueError(f"Vector must be 768-dim, got {vector.shape}")

    try:
        with h5py.File(corpus_path, 'a') as f:
            embeddings = f["embeddings"]

            # Current size
            current_size = embeddings["interaction_id"].shape[0]
            new_size = current_size + 1

            # Resize datasets
            embeddings["interaction_id"].resize((new_size,))
            embeddings["vector"].resize((new_size, 768))
            embeddings["model"].resize((new_size,))

            # Append data
            embeddings["interaction_id"][current_size] = interaction_id
            embeddings["vector"][current_size] = vector
            embeddings["model"][current_size] = model

        logger.info(
            "embedding_appended",
            interaction_id=interaction_id,
            model=model,
            vector_dim=vector.shape[0]
        )

        return True

    except Exception as e:
        logger.error("embedding_append_failed", error=str(e), interaction_id=interaction_id)
        return False


def get_corpus_stats(corpus_path: str) -> Dict:
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
    from logger import get_logger

    logger = get_logger()

    try:
        with h5py.File(corpus_path, 'r') as f:
            interactions_count = f["interactions"]["session_id"].shape[0]
            embeddings_count = f["embeddings"]["interaction_id"].shape[0]

            # Get file size
            file_size = Path(corpus_path).stat().st_size

            # Get metadata
            metadata = dict(f["metadata"].attrs)

            stats = {
                "interactions_count": interactions_count,
                "embeddings_count": embeddings_count,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "created_at": metadata.get("created_at"),
                "version": metadata.get("version"),
                "schema_version": metadata.get("schema_version")
            }

            logger.info("corpus_stats_retrieved", **stats)

            return stats

    except Exception as e:
        logger.error("corpus_stats_failed", error=str(e))
        return {}


def read_interactions(corpus_path: str, limit: int = 10) -> List[Dict]:
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
        with h5py.File(corpus_path, 'r') as f:
            interactions_group = f["interactions"]
            total = interactions_group["session_id"].shape[0]

            if total == 0:
                return []

            # Read last N interactions
            start = max(0, total - limit)
            end = total

            results = []
            for i in range(start, end):
                interaction = {
                    "session_id": interactions_group["session_id"][i].decode('utf-8'),
                    "interaction_id": interactions_group["interaction_id"][i].decode('utf-8'),
                    "timestamp": interactions_group["timestamp"][i].decode('utf-8'),
                    "prompt": interactions_group["prompt"][i].decode('utf-8'),
                    "response": interactions_group["response"][i].decode('utf-8'),
                    "model": interactions_group["model"][i].decode('utf-8'),
                    "tokens": int(interactions_group["tokens"][i])
                }
                results.append(interaction)

            return results

    except Exception as e:
        from logger import get_logger
        logger = get_logger()
        logger.error("read_interactions_failed", error=str(e))
        return []


if __name__ == "__main__":
    # Demo
    from config_loader import load_config

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
