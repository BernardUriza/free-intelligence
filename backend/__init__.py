"""FI Backend - Organized by responsibility domains.

Modules:
  - app/           : FastAPI application, middlewares, entry points
  - api/           : REST API route handlers
  - services/      : Business logic and domain services
  - repositories/  : Data access patterns (Clean Architecture)
  - domain/        : Domain entities and business rules
  - providers/     : LLM adapters and external integrations
  - policy/        : Access control, validation, enforcement
  - infrastructure/: Workers, auth, cache, observability
"""

from __future__ import annotations

# Repository exports (used by domain services)
from backend.repositories.session_repository import SessionRepository

__all__ = [
    "SessionRepository",
]
