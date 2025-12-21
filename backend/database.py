"""Database dependencies for FastAPI.

Minimal implementation for development - replace with proper database setup.
"""

from __future__ import annotations

from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# TODO: Replace with proper database configuration
# For now, use SQLite in-memory for development
DATABASE_URL = "sqlite:///./test.db"

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
