from __future__ import annotations

from fastapi import APIRouter

from . import chat, diagnostics, introduction, stream

router = APIRouter()
router.include_router(introduction.router)
router.include_router(chat.router)
router.include_router(diagnostics.router)
router.include_router(stream.router)
