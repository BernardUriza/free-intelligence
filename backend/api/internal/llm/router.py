"""
Internal LLM Router - Free Intelligence

Agrupa todos los endpoints internos de LLM.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/llm", tags=["Internal LLM"])

# Import sub-routers
from . import chat, structured

router.include_router(chat.router)
router.include_router(structured.router)
