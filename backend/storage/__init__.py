"""Backward compatibility shim: Storage layer moved to packages/fi_common/storage

This module provides re-exports from fi_common.storage for backward compatibility.
All storage utilities have been moved to the shared fi_common package.

Deprecated: Use fi_common.storage.* directly instead.

Provides:
  - audio_storage: Audio file storage with session-based organization
  - corpus_ops: HDF5 corpus operations (append-only, immutable)
  - corpus_schema: HDF5 schema definitions
  - sessions_store: Session management
"""

from __future__ import annotations

# Re-export audio_storage functions
from fi_common.storage.audio_storage import (
    compute_sha256,
    get_audio_manifest,
    save_audio_file,
    validate_session_id,
)

# Re-export corpus_identity functions
from fi_common.storage.corpus_identity import (
    add_corpus_identity,
    generate_corpus_id,
    generate_owner_hash,
    get_corpus_identity,
    verify_corpus_ownership,
)

# Re-export corpus_ops functions
from fi_common.storage.corpus_ops import (
    append_embedding,
    append_interaction,
    append_interaction_with_embedding,
    get_corpus_stats,
    read_interactions,
)

# Re-export corpus_schema functions and classes
from fi_common.storage.corpus_schema import (
    CorpusSchema,
    init_corpus,
    init_corpus_from_config,
    validate_corpus,
)

# Re-export search functions
from fi_common.storage.search import (
    cosine_similarity,
    search_by_session,
    semantic_search,
)

# Re-export sessions_store functions and classes
from fi_common.storage.sessions_store import Session, SessionsStore, generate_ulid

__all__ = [
    # audio_storage
    "compute_sha256",
    "get_audio_manifest",
    "save_audio_file",
    "validate_session_id",
    # corpus_identity
    "add_corpus_identity",
    "generate_corpus_id",
    "generate_owner_hash",
    "get_corpus_identity",
    "verify_corpus_ownership",
    # corpus_ops
    "append_embedding",
    "append_interaction",
    "append_interaction_with_embedding",
    "get_corpus_stats",
    "read_interactions",
    # corpus_schema
    "CorpusSchema",
    "init_corpus",
    "init_corpus_from_config",
    "validate_corpus",
    # search
    "cosine_similarity",
    "search_by_session",
    "semantic_search",
    # sessions_store
    "Session",
    "SessionsStore",
    "generate_ulid",
]
