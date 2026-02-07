"""Internal LLM API - Ultra-observable chat endpoints.

Protected by InternalOnlyMiddleware - not accessible from external requests.

Endpoints:
- POST /llm/chat - Main chat with full observability
- POST /llm/chat/stream - Server-Sent Events streaming
- POST /llm/chat/debug - Debug endpoint for introspection
- POST /llm/structured-extract - Structured JSON extraction

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Infrastructure Migration)
"""

from fastapi import APIRouter

from .chat import router as chat_router
from .structured import router as structured_router
from .schemas import ChatRequest, ChatResponse, StructuredRequest, StructuredResponse

# Aggregate router
router = APIRouter(prefix="/llm", tags=["Internal LLM"])
router.include_router(chat_router)
router.include_router(structured_router)

__all__ = [
    "router",
    "ChatRequest",
    "ChatResponse",
    "StructuredRequest",
    "StructuredResponse",
]
