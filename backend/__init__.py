"""FI Backend - Organized by responsibility domains.

Modules:
  - app/           : FastAPI application, middlewares, entry points
  - api/           : REST API route handlers
  - services/      : Business logic and domain services
  - jobs/          : Background workers and async jobs
  - storage/       : Data layer (HDF5, audio, sessions)
  - providers/     : LLM adapters and external integrations
  - policy/        : Access control, validation, enforcement
  - schemas/       : Data models, validators, event definitions
  - common/        : Shared utilities (logger, config, cache, etc)
  - security/      : Security utilities (IP validation, etc)
  - repositories/  : Data access patterns
  - cli/           : Command-line tools
  - tools/         : Utility scripts and helpers

Quick import aliases (reduces 7-level imports to 2 levels):
  from backend import get_logger       # vs backend.utils.common.logging.logger
  from backend import HDF5SessionStore # vs backend.core.infrastructure.hdf5.sessions_store
"""

from __future__ import annotations

# Common utilities (most frequently imported)
from backend.utils.common.logging.logger import get_logger

# Storage layer (frequently used)
# Note: Path is ugly (infrastructure/storage/infrastructure/hdf5) - pending refactor
from infrastructure.storage.infrastructure.hdf5.sessions_store import SessionsStore

# Domain entities (clean imports)
# Note: Full domain extraction pending (see .claude/rules/architecture/backend-refactor-analysis.md)

__all__ = [
    "get_logger",
    "SessionsStore",
]
