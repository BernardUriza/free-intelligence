"""Utility functions for timeline verify API.

Provides helper functions for hash computation and verification.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

import h5py

from .config import CORPUS_PATH, logger


def compute_hash_for_target(target_id: str) -> tuple[str, Optional[str]]:
    """Compute SHA256 hash for a session or event.

    Args:
        target_id: Session ID or event ID to compute hash for

    Returns:
        Tuple of (hash_hex, error_msg). If error_msg is not None, hash_hex is empty.
    """
    try:
        with h5py.File(CORPUS_PATH, "r") as corpus:
            # Try session first
            session_path = f"/sessions/{target_id}"

            if session_path in corpus:
                # It's a session: hash all interactions
                session_group = corpus[session_path]

                # Collect all interaction hashes in order
                interaction_ids = sorted(
                    [
                        k
                        for k in session_group.keys()  # type: ignore[attr-defined, union-attr]
                        if k.startswith("interaction_")
                    ]
                )

                hash_chain = hashlib.sha256()

                for int_id in interaction_ids:
                    interaction_group = session_group[int_id]

                    # Read content_hash from metadata
                    if "metadata" in interaction_group:
                        metadata_ds = interaction_group["metadata"]
                        content_hash = (
                            metadata_ds.attrs.get("content_hash", b"").decode()  # type: ignore[attr-defined, union-attr]
                            if isinstance(
                                metadata_ds.attrs.get("content_hash"),
                                bytes,  # type: ignore[attr-defined, union-attr]
                            )
                            else str(metadata_ds.attrs.get("content_hash", ""))  # type: ignore[attr-defined, union-attr]
                        )

                        if content_hash:
                            hash_chain.update(content_hash.encode())

                return hash_chain.hexdigest(), None

            # Try interaction (search across all sessions)
            for session_id in corpus["/sessions"].keys():  # type: ignore[attr-defined, union-attr, index]
                session_group = corpus[f"/sessions/{session_id}"]  # type: ignore[index, assignment]
                if f"interaction_{target_id}" in session_group:  # type: ignore[operator]
                    int_group = session_group[f"interaction_{target_id}"]  # type: ignore[index, assignment]
                    if "metadata" in int_group:  # type: ignore[operator]
                        metadata_ds = int_group["metadata"]  # type: ignore[index, assignment]
                        content_hash = (
                            metadata_ds.attrs.get("content_hash", b"").decode()  # type: ignore[attr-defined, union-attr]
                            if isinstance(
                                metadata_ds.attrs.get("content_hash"),
                                bytes,  # type: ignore[attr-defined, union-attr]
                            )
                            else str(metadata_ds.attrs.get("content_hash", ""))  # type: ignore[attr-defined, union-attr]
                        )
                        if content_hash:
                            return content_hash, None

            return "", f"Target {target_id} not found in corpus"

    except Exception as e:
        logger.error("Error computing hash for %s: %s", target_id, str(e))
        return "", f"Hash computation failed: {str(e)}"


def get_hash_prefix(hash_value: str, prefix_length: int = 16) -> str:
    """Extract hash prefix for logging/display (privacy).

    Args:
        hash_value: Full hash string
        prefix_length: Length of prefix to extract

    Returns:
        Hash prefix or "N/A" if hash is empty
    """
    return hash_value[:prefix_length] if hash_value else "N/A"


def build_summary(
    total: int,
    valid_count: int,
    invalid_count: int,
    duration_ms: int,
) -> dict[str, Any]:
    """Build summary statistics for response.

    Args:
        total: Total number of items verified
        valid_count: Number of valid hashes
        invalid_count: Number of invalid hashes
        duration_ms: Duration in milliseconds

    Returns:
        Summary dictionary with statistics
    """
    return {
        "total": total,
        "valid": valid_count,
        "invalid": invalid_count,
        "duration_ms": duration_ms,
    }
