"""Assistant Domain - AI chat with configurable personas.

Endpoints:
- POST /chat - Send message to AI assistant
- POST /chat/stream - Stream AI response
- POST /introduction - Get persona introduction
- GET  /history/paginated - Get conversation history
- GET  /history/stats - Get history statistics
- POST /history/search - Search conversation history
- GET  /ws/stats - Get WebSocket stats

Migrated from: backend/api/routers/assistant/public/
"""

from __future__ import annotations
