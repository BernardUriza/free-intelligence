"""Database dependencies for FastAPI.

Minimal implementation for development - replace with proper database setup.
"""

from __future__ import annotations

from collections.abc import Iterator

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Load .env before reading DATABASE_URL (this module may be imported before secrets.py)
load_dotenv()

# Read database URL from environment — MUST be PostgreSQL, never SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it in .env (e.g. postgresql://user@localhost:5432/aurity)"
    )

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_dependency() -> Iterator[Session]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
