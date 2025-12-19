"""fi_storage - Storage layer for Free Intelligence.

Provides HDF5-based persistence, repositories, and session management.

Public API:
    - TaskRepository: Task persistence with HDF5
    - SessionH5Manager: Session file management
    - SessionsStore: Session CRUD operations
    - corpus_ops: Append-only corpus operations
"""

from __future__ import annotations


# Re-export main classes (lazy imports to avoid circular deps)
def __getattr__(name: str):
    if name == "TaskRepository":
        from .infrastructure.hdf5.task_repository import TaskRepository

        return TaskRepository
    if name == "SessionH5Manager":
        from .infrastructure.hdf5.session_h5_manager import SessionH5Manager

        return SessionH5Manager
    if name == "SessionsStore":
        from .infrastructure.hdf5.sessions_store import SessionsStore

        return SessionsStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SessionH5Manager",
    "SessionsStore",
    "TaskRepository",
]
