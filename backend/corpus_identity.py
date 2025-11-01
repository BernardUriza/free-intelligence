#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Corpus Identity Management

Provides corpus_id generation, owner_hash generation, and ownership verification.
Ensures every corpus has a unique identifier and traceable ownership.

FI-DATA-FEAT-004
"""

import hashlib
import uuid
from pathlib import Path
from typing import Optional

import h5py


def generate_corpus_id() -> str:
    """
    Generate unique corpus identifier using UUID v4.

    Returns:
        UUID v4 string (36 characters)

    Examples:
        >>> corpus_id = generate_corpus_id()
        >>> len(corpus_id)
        36
        >>> corpus_id.count('-')
        4
    """
    return str(uuid.uuid4())


def generate_owner_hash(owner_identifier: str, salt: Optional[str] = None) -> str:
    """
    Generate SHA256 hash of owner identifier.

    Args:
        owner_identifier: Username, email, or unique identifier
        salt: Optional salt for hashing (default: None)

    Returns:
        SHA256 hash (64 hex characters)

    Examples:
        >>> owner_hash = generate_owner_hash("bernard@example.com")
        >>> len(owner_hash)
        64

        >>> # With salt for additional security
        >>> owner_hash = generate_owner_hash("bernard@example.com", salt="secret")
        >>> len(owner_hash)
        64
    """
    if not owner_identifier:
        raise ValueError("owner_identifier cannot be empty")

    # Combine identifier with salt if provided
    data = owner_identifier
    if salt:
        data = f"{owner_identifier}{salt}"

    # Generate SHA256 hash
    hash_object = hashlib.sha256(data.encode("utf-8"))
    return hash_object.hexdigest()


def add_corpus_identity(
    corpus_path: str,
    owner_identifier: str,
    corpus_id: Optional[str] = None,
    salt: Optional[str] = None,
) -> tuple[str, str]:
    """
    Add corpus_id and owner_hash to existing corpus.

    Args:
        corpus_path: Path to HDF5 corpus file
        owner_identifier: Username, email, or unique identifier
        corpus_id: Optional pre-generated corpus_id (auto-generated if None)
        salt: Optional salt for owner_hash

    Returns:
        Tuple of (corpus_id, owner_hash)

    Raises:
        FileNotFoundError: If corpus file doesn't exist
        ValueError: If corpus already has identity attributes

    Examples:
        >>> corpus_id, owner_hash = add_corpus_identity(
        ...     "storage/corpus.h5",
        ...     "bernard@example.com"
        ... )
        >>> print(f"Corpus ID: {corpus_id}")
        >>> print(f"Owner Hash: {owner_hash}")
    """
    from logger import get_logger

    logger = get_logger()
    path = Path(corpus_path)

    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    # Generate IDs
    if corpus_id is None:
        corpus_id = generate_corpus_id()

    owner_hash = generate_owner_hash(owner_identifier, salt=salt)

    try:
        with h5py.File(corpus_path, "a") as f:
            metadata = f["metadata"]

            # Check if identity already exists
            if "corpus_id" in metadata.attrs:
                existing_id = metadata.attrs["corpus_id"]
                raise ValueError(
                    f"Corpus already has identity (corpus_id: {existing_id}). " + "Cannot overwrite."
                )

            # Add identity attributes
            metadata.attrs["corpus_id"] = corpus_id
            metadata.attrs["owner_hash"] = owner_hash

        logger.info(
            "CORPUS_IDENTITY_ADDED",
            corpus_id=corpus_id,
            owner_hash=owner_hash[:16] + "...",  # Log only prefix for security
            path=str(path),
        )

        return corpus_id, owner_hash

    except Exception as e:
        logger.error("CORPUS_IDENTITY_ADD_FAILED", error=str(e), path=str(path))
        raise


def verify_corpus_ownership(
    corpus_path: str, owner_identifier: str, salt: Optional[str] = None
) -> bool:
    """
    Verify ownership of a corpus by comparing owner_hash.

    Args:
        corpus_path: Path to HDF5 corpus file
        owner_identifier: Username, email, or unique identifier to verify
        salt: Optional salt used during hash generation

    Returns:
        True if owner_hash matches, False otherwise

    Examples:
        >>> # Add identity
        >>> add_corpus_identity("storage/corpus.h5", "bernard@example.com")

        >>> # Verify ownership
        >>> is_owner = verify_corpus_ownership("storage/corpus.h5", "bernard@example.com")
        >>> print(f"Is owner: {is_owner}")  # True

        >>> # Wrong owner
        >>> is_owner = verify_corpus_ownership("storage/corpus.h5", "other@example.com")
        >>> print(f"Is owner: {is_owner}")  # False
    """
    from logger import get_logger

    logger = get_logger()

    try:
        with h5py.File(corpus_path, "r") as f:
            metadata = f["metadata"]

            if "owner_hash" not in metadata.attrs:
                logger.warning(
                    "CORPUS_VERIFICATION_FAILED", reason="No owner_hash attribute", path=corpus_path
                )
                return False

            stored_hash = metadata.attrs["owner_hash"]

        # Generate hash from provided identifier
        computed_hash = generate_owner_hash(owner_identifier, salt=salt)

        # Compare hashes
        is_match = stored_hash == computed_hash

        if is_match:
            logger.info("OWNERSHIP_HASH_MATCHED", path=corpus_path)
        else:
            logger.warning("OWNERSHIP_HASH_MISMATCH", path=corpus_path)

        return is_match

    except Exception as e:
        logger.error("CORPUS_VERIFICATION_ERROR", error=str(e), path=corpus_path)
        return False


def get_corpus_identity(corpus_path: str) -> Optional[dict]:
    """
    Retrieve corpus identity information.

    Args:
        corpus_path: Path to HDF5 corpus file

    Returns:
        Dictionary with corpus_id and owner_hash, or None if not set

    Examples:
        >>> identity = get_corpus_identity("storage/corpus.h5")
        >>> if identity:
        ...     print(f"Corpus ID: {identity['corpus_id']}")
        ...     print(f"Owner Hash: {identity['owner_hash']}")
    """
    from logger import get_logger

    logger = get_logger()

    try:
        with h5py.File(corpus_path, "r") as f:
            metadata = f["metadata"]

            if "corpus_id" not in metadata.attrs or "owner_hash" not in metadata.attrs:
                logger.info("CORPUS_IDENTITY_NOT_SET", path=corpus_path)
                return None

            identity = {
                "corpus_id": metadata.attrs["corpus_id"],
                "owner_hash": metadata.attrs["owner_hash"],
                "created_at": metadata.attrs.get("created_at"),
                "version": metadata.attrs.get("version"),
                "schema_version": metadata.attrs.get("schema_version"),
            }

            logger.info("IDENTITY_METADATA_READ", corpus_id=identity["corpus_id"], path=corpus_path)

            return identity

    except Exception as e:
        logger.error("CORPUS_IDENTITY_RETRIEVAL_FAILED", error=str(e), path=corpus_path)
        return None


if __name__ == "__main__":
    # CLI demonstration
    import sys

    from config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    if len(sys.argv) > 1 and sys.argv[1] == "add":
        # Add identity
        if len(sys.argv) < 3:
            print("Usage: python3 corpus_identity.py add <owner_identifier> [salt]")
            sys.exit(1)

        owner_identifier = sys.argv[2]
        salt = sys.argv[3] if len(sys.argv) > 3 else None

        try:
            corpus_id, owner_hash = add_corpus_identity(corpus_path, owner_identifier, salt=salt)
            print("✅ Identity added:")
            print(f"   Corpus ID: {corpus_id}")
            print(f"   Owner Hash: {owner_hash}")
        except Exception as e:
            print(f"❌ Failed to add identity: {e}")
            sys.exit(1)

    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        # Verify ownership
        if len(sys.argv) < 3:
            print("Usage: python3 corpus_identity.py verify <owner_identifier> [salt]")
            sys.exit(1)

        owner_identifier = sys.argv[2]
        salt = sys.argv[3] if len(sys.argv) > 3 else None

        is_owner = verify_corpus_ownership(corpus_path, owner_identifier, salt=salt)
        if is_owner:
            print("✅ Ownership verified")
        else:
            print("❌ Ownership verification failed")
            sys.exit(1)

    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        # Show identity
        identity = get_corpus_identity(corpus_path)
        if identity:
            print("📋 Corpus Identity:")
            for key, value in identity.items():
                print(f"   {key}: {value}")
        else:
            print("❌ No identity set for this corpus")

    else:
        print("Usage:")
        print("  python3 corpus_identity.py add <owner_identifier> [salt]")
        print("  python3 corpus_identity.py verify <owner_identifier> [salt]")
        print("  python3 corpus_identity.py show")
