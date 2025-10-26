#!/usr/bin/env python3
"""
Free Intelligence - HDF5 Corpus Schema

Hierarchical schema for storing interactions, embeddings, and metadata.
Structure: /interactions/, /embeddings/, /metadata/

FI-DATA-FEAT-001
"""

import h5py
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class CorpusSchema:
    """HDF5 corpus schema definition and validation."""

    # Required top-level groups
    REQUIRED_GROUPS = ["interactions", "embeddings", "metadata"]

    # Dataset specifications for interactions
    INTERACTION_DATASETS = {
        "session_id": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "interaction_id": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "timestamp": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "prompt": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "response": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "model": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "tokens": {"dtype": "int32"}
    }

    # Dataset specifications for embeddings
    EMBEDDING_DATASETS = {
        "interaction_id": {"dtype": h5py.string_dtype(encoding='utf-8')},
        "vector": {"dtype": "float32"},  # Will be 2D array
        "model": {"dtype": h5py.string_dtype(encoding='utf-8')}
    }

    @classmethod
    def validate(cls, corpus_path: str) -> List[str]:
        """
        Validate HDF5 corpus schema.

        Args:
            corpus_path: Path to HDF5 corpus file

        Returns:
            List of validation errors (empty if valid)

        Examples:
            >>> errors = CorpusSchema.validate("storage/corpus.h5")
            >>> if not errors:
            ...     print("Schema is valid")
        """
        errors = []
        path = Path(corpus_path)

        if not path.exists():
            errors.append(f"Corpus file not found: {corpus_path}")
            return errors

        try:
            with h5py.File(corpus_path, 'r') as f:
                # Check required groups
                for group in cls.REQUIRED_GROUPS:
                    if group not in f:
                        errors.append(f"Missing required group: /{group}")

                # Validate interactions group structure
                if "interactions" in f:
                    interactions = f["interactions"]
                    for dataset_name in cls.INTERACTION_DATASETS:
                        if dataset_name not in interactions:
                            errors.append(f"Missing dataset: /interactions/{dataset_name}")

                # Validate embeddings group structure
                if "embeddings" in f:
                    embeddings = f["embeddings"]
                    for dataset_name in cls.EMBEDDING_DATASETS:
                        if dataset_name not in embeddings:
                            errors.append(f"Missing dataset: /embeddings/{dataset_name}")

        except Exception as e:
            errors.append(f"Error reading HDF5 file: {e}")

        return errors


def init_corpus(
    corpus_path: str,
    owner_identifier: str,
    force: bool = False,
    salt: Optional[str] = None
) -> bool:
    """
    Initialize HDF5 corpus with hierarchical schema and identity.

    Creates the following structure:
    - /interactions/: Stores prompt-response pairs with metadata
    - /embeddings/: Stores vector embeddings for semantic search
    - /metadata/: Stores system metadata, configuration, and identity

    Args:
        corpus_path: Path where corpus.h5 will be created
        owner_identifier: Username, email, or unique identifier for ownership
        force: If True, overwrites existing file (default: False)
        salt: Optional salt for owner_hash generation

    Returns:
        True if initialization successful, False otherwise

    Raises:
        FileExistsError: If file exists and force=False

    Examples:
        >>> init_corpus("storage/corpus.h5", "bernard@example.com")
        True

        >>> init_corpus("storage/corpus.h5", "bernard@example.com", force=True)
        True  # Overwrites existing file
    """
    from logger import get_logger
    from corpus_identity import generate_corpus_id, generate_owner_hash

    logger = get_logger()
    path = Path(corpus_path)

    # Check if file exists
    if path.exists() and not force:
        logger.error("CORPUS_INIT_FAILED", reason="File already exists", path=str(path))
        raise FileExistsError(f"Corpus already exists: {corpus_path}. Use force=True to overwrite.")

    # Create parent directory
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with h5py.File(corpus_path, 'w') as f:
            # Create /interactions/ group with datasets
            interactions = f.create_group("interactions")
            for dataset_name, spec in CorpusSchema.INTERACTION_DATASETS.items():
                interactions.create_dataset(
                    dataset_name,
                    shape=(0,),
                    maxshape=(None,),
                    dtype=spec["dtype"],
                    chunks=True,  # Auto-chunking for optimal access
                    compression="gzip",  # Portable compression
                    compression_opts=4  # Balanced compression level (1-9)
                )

            # Create /embeddings/ group with datasets
            embeddings = f.create_group("embeddings")
            embeddings.create_dataset(
                "interaction_id",
                shape=(0,),
                maxshape=(None,),
                dtype=CorpusSchema.EMBEDDING_DATASETS["interaction_id"]["dtype"],
                chunks=True,
                compression="gzip",
                compression_opts=4
            )
            embeddings.create_dataset(
                "vector",
                shape=(0, 768),  # 768-dim embeddings (all-MiniLM-L6-v2)
                maxshape=(None, 768),
                dtype=CorpusSchema.EMBEDDING_DATASETS["vector"]["dtype"],
                chunks=True,
                compression="gzip",
                compression_opts=4  # Vectors compress well
            )
            embeddings.create_dataset(
                "model",
                shape=(0,),
                maxshape=(None,),
                dtype=CorpusSchema.EMBEDDING_DATASETS["model"]["dtype"],
                chunks=True,
                compression="gzip",
                compression_opts=4
            )

            # Create /metadata/ group with system info and identity
            metadata = f.create_group("metadata")
            metadata.attrs["created_at"] = datetime.now().isoformat()
            metadata.attrs["version"] = "0.1.0"
            metadata.attrs["schema_version"] = "1"

            # Add identity attributes
            metadata.attrs["corpus_id"] = generate_corpus_id()
            metadata.attrs["owner_hash"] = generate_owner_hash(owner_identifier, salt=salt)

        # Log initialization with identity info (partial hash for security)
        with h5py.File(corpus_path, 'r') as f:
            corpus_id = f["metadata"].attrs["corpus_id"]
            owner_hash = f["metadata"].attrs["owner_hash"]

        logger.info(
            "CORPUS_INITIALIZED",
            path=str(path),
            groups=CorpusSchema.REQUIRED_GROUPS,
            corpus_id=corpus_id,
            owner_hash=owner_hash[:16] + "..."  # Log only prefix
        )
        return True

    except Exception as e:
        logger.error("CORPUS_INIT_FAILED", error=str(e), path=str(path))
        return False


def init_corpus_from_config(
    owner_identifier: str,
    config_path: Optional[str] = None,
    force: bool = False,
    salt: Optional[str] = None
) -> bool:
    """
    Initialize corpus using path from config.yml.

    Args:
        owner_identifier: Username, email, or unique identifier for ownership
        config_path: Optional path to config file
        force: If True, overwrites existing file
        salt: Optional salt for owner_hash generation

    Returns:
        True if initialization successful

    Examples:
        >>> init_corpus_from_config("bernard@example.com")
        True
    """
    from config_loader import load_config

    config = load_config(config_path)
    corpus_path = config["storage"]["corpus_path"]

    return init_corpus(corpus_path, owner_identifier, force=force, salt=salt)


def validate_corpus(corpus_path: Optional[str] = None) -> Dict[str, any]:
    """
    Validate corpus schema and return status.

    Args:
        corpus_path: Path to corpus file. If None, reads from config.

    Returns:
        Dictionary with validation results:
        - valid: bool
        - errors: List[str]
        - path: str

    Examples:
        >>> result = validate_corpus()
        >>> if result["valid"]:
        ...     print("Corpus is valid")
    """
    from logger import get_logger

    logger = get_logger()

    if corpus_path is None:
        from config_loader import load_config
        config = load_config()
        corpus_path = config["storage"]["corpus_path"]

    errors = CorpusSchema.validate(corpus_path)

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "path": corpus_path
    }

    if result["valid"]:
        logger.info("CORPUS_SCHEMA_CHECKS_COMPLETED", path=corpus_path, issues_found=0)
    else:
        logger.warning("CORPUS_SCHEMA_CHECKS_COMPLETED", path=corpus_path, issues_found=len(errors), errors=errors)

    return result


if __name__ == "__main__":
    # CLI demonstration
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        # Initialize corpus
        if len(sys.argv) < 3:
            print("Usage: python3 corpus_schema.py init <owner_identifier> [--force]")
            print("Example: python3 corpus_schema.py init bernard@example.com")
            sys.exit(1)

        owner_identifier = sys.argv[2]
        force = "--force" in sys.argv

        success = init_corpus_from_config(owner_identifier, force=force)
        if success:
            print("✅ Corpus initialized successfully")
            result = validate_corpus()
            print(f"   Path: {result['path']}")
            print(f"   Valid: {result['valid']}")

            # Show identity
            from corpus_identity import get_corpus_identity
            identity = get_corpus_identity(result['path'])
            if identity:
                print(f"   Corpus ID: {identity['corpus_id']}")
                print(f"   Owner Hash: {identity['owner_hash'][:16]}...")
        else:
            print("❌ Corpus initialization failed")
            sys.exit(1)

    elif len(sys.argv) > 1 and sys.argv[1] == "validate":
        # Validate existing corpus
        result = validate_corpus()
        print(f"Corpus: {result['path']}")
        print(f"Valid: {result['valid']}")
        if not result["valid"]:
            print("\nErrors:")
            for error in result["errors"]:
                print(f"  - {error}")
            sys.exit(1)

    else:
        print("Usage:")
        print("  python3 corpus_schema.py init <owner_identifier> [--force]")
        print("  python3 corpus_schema.py validate")
