"""Assistant Domain - AI chat with configurable personas.

Sub-modules:
- chat: Main chat endpoint (OpenAI-style)
- stream: SSE streaming responses
- introduction: Onboarding greeting
- history: Conversation history search
- schemas: Pydantic models

Endpoints (8 total):
- POST /chat - Send message to AI assistant
- POST /chat/stream - Stream AI response via SSE
- POST /introduction - Get persona introduction
- POST /history/search - Search conversation history
- GET  /history/timeline - Get timeline of sessions
- GET  /history/stats - Get history statistics
- GET  /history/paginated - Get paginated history

Features:
- OpenAI-style chat completions API
- Multiple personas (general_assistant, onboarding_guide, etc.)
- Emotional analysis from behavior metrics
- RAG context injection (HIPAA-compliant)
- Conversation memory with semantic search

Migrated from: backend/api/routers/assistant/public/
"""

from __future__ import annotations

from fastapi import APIRouter

from . import chat, history, introduction, personas, stream

router = APIRouter()
router.include_router(chat.router)
router.include_router(stream.router)
router.include_router(introduction.router)
router.include_router(history.router)
router.include_router(personas.router)  # GET /personas
