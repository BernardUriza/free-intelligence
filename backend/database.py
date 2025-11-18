"""Database configuration for PostgreSQL.

SQLAlchemy setup for PostgreSQL connection and session management.
Uses connection pooling and automatic session cleanup.

Author: Bernard Uriza Orozco
Created: 2025-11-17
Card: FI-DATA-DB-001
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.logger import get_logger
from backend.models.db_models import Base

# Load .env file BEFORE reading environment variables
load_dotenv()

logger = get_logger(__name__)

# Database URL from environment
# SECURITY: Never commit actual credentials. Use environment variables.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/dbname",  # Placeholder only
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Maximum overflow connections
    pool_pre_ping=True,  # Verify connections before use
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables.

    Creates all tables defined in models if they don't exist.
    Should be called at application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("DATABASE_TABLES_INITIALIZED", tables=list(Base.metadata.tables.keys()))
    except Exception as e:
        logger.error("DATABASE_INIT_FAILED", error=str(e))
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup.

    Usage:
        with get_db() as db:
            patient = db.query(Patient).filter_by(patient_id=id).first()

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_dependency() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions.

    Usage in FastAPI:
        @app.get("/patients")
        def list_patients(db: Session = Depends(get_db_dependency)):
            return db.query(Patient).all()

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
