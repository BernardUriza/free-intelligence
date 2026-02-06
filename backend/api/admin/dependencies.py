"""Admin API Dependencies - FastAPI DI providers.

Provides UserService dependency for admin routers.
"""

from __future__ import annotations

from backend.database import get_db_dependency
from backend.infrastructure.auth.services.user_service import UserService
from fastapi import Depends
from sqlalchemy.orm import Session


def get_user_service_dep(db: Session = Depends(get_db_dependency)) -> UserService:
    """Get UserService for admin endpoints."""
    return UserService(db)
