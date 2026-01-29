from __future__ import annotations

from fastapi import APIRouter

# Thin wrapper to preserve import path while delegating to the modular package
from .sessions import router as sessions_router

router = APIRouter()
router.include_router(sessions_router)
