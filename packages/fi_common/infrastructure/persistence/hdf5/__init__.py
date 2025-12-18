from __future__ import annotations

"""HDF5 persistence adapters (bridge to existing storage modules).

These modules re-export current storage implementations while we migrate them
into fi_common. Replace direct backend.storage imports with these adapters to
prepare for clean moves without breaking callers.
"""

__all__ = [
    "audio_storage",
    "corpus_identity",
    "corpus_ops",
    "corpus_schema",
    "fi_corpus_api",
    "search",
    "sessions_store",
    "task_repository",
    "session_h5_manager",
    "session_locks",
    "utils",
    "h5py_utils",
]
