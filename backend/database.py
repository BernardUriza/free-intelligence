"""Database dependencies for FastAPI.

Minimal implementation for development - replace with proper database setup.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Read database URL from environment, with fallback for development
# Use absolute path for SQLite to work from any working directory (backend/ or project root)
PROJECT_ROOT = Path(__file__).parent.parent  # backend/database.py -> project root
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/test.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_dependency() -> Iterator[Session]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for backward compatibility
get_db = get_db_dependency
