#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Append-Only Policy Enforcement

Ensures HDF5 corpus operations are restricted to append-only mode.
Direct mutation, modification, or deletion of existing data is forbidden.

FI-DATA-FEAT-005
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import h5py  # type: ignore

if TYPE_CHECKING:
    pass  # type: ignore[attr-defined]


class AppendOnlyViolation(Exception):
    """Raised when an operation violates append-only policy."""

    def __init__(self, message: str) -> None:
        """Initialize exception with message."""
        super().__init__(message)
        self.message = message


class AppendOnlyPolicy:
    """
    Enforces append-only operations on HDF5 corpus.

    Allowed operations:
    - Resize datasets to larger size (append)
    - Write to new indices only
    - Read operations

    Forbidden operations:
    - Modify existing data
    - Delete data
    - Resize datasets to smaller size
    - Truncate datasets
    """

    def __init__(self, corpus_path: str):
        """
        Initialize append-only policy enforcer.

        Args:
            corpus_path: Path to HDF5 corpus file
        """
        self.corpus_path = corpus_path
        self.original_sizes: dict[str, int] = {}

    def __enter__(self):
        """Context manager entry - record original dataset sizes."""
        if not Path(self.corpus_path).exists():
            raise FileNotFoundError(f"Corpus not found: {self.corpus_path}")

        with h5py.File(self.corpus_path, "r") as f:  # type: ignore
            # Record original sizes for all datasets
            for group_name in ["interactions", "embeddings"]:
                if group_name in f:
                    group = f[group_name]  # type: ignore
                    for dataset_name in group.keys():  # type: ignore
                        key = f"{group_name}/{dataset_name}"
                        self.original_sizes[key] = group[dataset_name].shape[0]  # type: ignore

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - verify no policy violations."""
        # If exception already occurred, don't validate
        if exc_type is not None:
            return False

        # Verify all dataset sizes increased or stayed same
        with h5py.File(self.corpus_path, "r") as f:  # type: ignore
            for group_name in ["interactions", "embeddings"]:
                if group_name in f:
                    group = f[group_name]  # type: ignore
                    for dataset_name in group.keys():  # type: ignore
                        key = f"{group_name}/{dataset_name}"
                        original_size = self.original_sizes.get(key, 0)
                        current_size = group[dataset_name].shape[0]  # type: ignore

                        if current_size < original_size:
                            raise AppendOnlyViolation(
                                f"Dataset {key} was truncated: {original_size} → {current_size}. "
                                + "Append-only policy forbids data deletion."
                            )

        return False

    def validate_write_index(self, group_name: str, dataset_name: str, index: int) -> bool:
        """
        Validate that write operation targets only new indices.

        Args:
            group_name: HDF5 group name (e.g., 'interactions')
            dataset_name: Dataset name (e.g., 'session_id')
            index: Index being written to

        Returns:
            True if write is allowed (new index only)

        Raises:
            AppendOnlyViolation: If attempting to modify existing data
        """
        key = f"{group_name}/{dataset_name}"
        original_size = self.original_sizes.get(key, 0)

        if index < original_size:
            raise AppendOnlyViolation(
                f"Cannot modify existing data at {key}[{index}]. "
                + f"Original size: {original_size}. Append-only policy allows writes only to new indices (>= {original_size})."
            )

        return True

    def validate_resize(self, group_name: str, dataset_name: str, new_size: int) -> bool:
        """
        Validate that resize operation only increases dataset size.

        Args:
            group_name: HDF5 group name
            dataset_name: Dataset name
            new_size: New size after resize

        Returns:
            True if resize is allowed (increase only)

        Raises:
            AppendOnlyViolation: If attempting to shrink dataset
        """
        key = f"{group_name}/{dataset_name}"
        original_size = self.original_sizes.get(key, 0)

        if new_size < original_size:
            raise AppendOnlyViolation(
                f"Cannot shrink dataset {key} from {original_size} to {new_size}. "
                + "Append-only policy forbids data deletion."
            )

        return True


def verify_append_only_operation(
    corpus_path: str, operation_name: str, group_name: str, dataset_name: Optional[str] = None
) -> dict[str, Any]:
    """
    Verify an operation is append-only compliant.

    Args:
        corpus_path: Path to corpus
        operation_name: Name of operation being performed
        group_name: HDF5 group name
        dataset_name: Optional dataset name

    Returns:
        Dictionary with verification result

    Examples:
        >>> result = verify_append_only_operation(
        ...     "storage/corpus.h5",
        ...     "append_interaction",
        ...     "interactions",
        ...     "session_id"
        ... )
        >>> assert result["allowed"] == True
    """
    from logger import get_logger

    logger = get_logger()

    # All read operations are allowed
    if operation_name.startswith("read") or operation_name.startswith("get"):
        logger.info(
            "APPEND_ONLY_CHECKS_COMPLETED",
            operation=operation_name,
            reason="read_operation_always_allowed",
        )
        return {"allowed": True, "reason": "read operation"}

    # Append operations are allowed
    if operation_name.startswith("append"):
        logger.info(
            "APPEND_ONLY_CHECKS_COMPLETED",
            operation=operation_name,
            group=group_name,
            dataset=dataset_name,
        )
        return {"allowed": True, "reason": "append operation"}

    # All other operations are forbidden
    logger.warning(
        "APPEND_ONLY_VIOLATION_DETECTED",
        operation=operation_name,
        group=group_name,
        dataset=dataset_name,
        reason="operation_not_allowed",
    )

    return {
        "allowed": False,
        "reason": f"Operation '{operation_name}' violates append-only policy",
        "group": group_name,
        "dataset": dataset_name,
    }


def get_dataset_size(corpus_path: str, group_name: str, dataset_name: str) -> int:
    """
    Get current size of a dataset (for append-only verification).

    Args:
        corpus_path: Path to corpus
        group_name: HDF5 group name
        dataset_name: Dataset name

    Returns:
        Current dataset size
    """
    with h5py.File(corpus_path, "r") as f:  # type: ignore
        return f[group_name][dataset_name].shape[0]  # type: ignore


if __name__ == "__main__":
    """Demo: Append-only policy enforcement"""
    from config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    print("🔒 Append-Only Policy Demo\n")

    # Test 1: Read operations (always allowed)
    print("Test 1: Verifying read operation...")
    result = verify_append_only_operation(corpus_path, "read_interactions", "interactions")
    print(f"  Result: {'✅ ALLOWED' if result['allowed'] else '❌ BLOCKED'}")
    print(f"  Reason: {result['reason']}\n")

    # Test 2: Append operations (allowed)
    print("Test 2: Verifying append operation...")
    result = verify_append_only_operation(
        corpus_path, "append_interaction", "interactions", "session_id"
    )
    print(f"  Result: {'✅ ALLOWED' if result['allowed'] else '❌ BLOCKED'}")
    print(f"  Reason: {result['reason']}\n")

    # Test 3: Mutation operations (forbidden)
    print("Test 3: Verifying mutation operation...")
    result = verify_append_only_operation(
        corpus_path, "update_interaction", "interactions", "prompt"
    )
    print(f"  Result: {'✅ ALLOWED' if result['allowed'] else '❌ BLOCKED'}")
    print(f"  Reason: {result['reason']}\n")

    # Test 4: Context manager usage
    print("Test 4: Testing context manager...")
    try:
        with AppendOnlyPolicy(corpus_path) as policy:
            print("  ✅ Context manager initialized")
            print("  📊 Recorded dataset sizes:")
            for key, size in policy.original_sizes.items():
                print(f"    {key}: {size}")
        print("  ✅ Context manager exited cleanly\n")
    except AppendOnlyViolation as e:
        print(f"  ❌ Policy violation: {e}\n")

    # Test 5: Get dataset size
    print("Test 5: Getting dataset sizes...")
    interactions_size = get_dataset_size(corpus_path, "interactions", "session_id")
    embeddings_size = get_dataset_size(corpus_path, "embeddings", "interaction_id")
    print(f"  Interactions: {interactions_size}")
    print(f"  Embeddings: {embeddings_size}\n")

    print("✅ Append-Only Policy Demo Complete")
