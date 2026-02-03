"""Timeline Domain - Session history and longitudinal memory.

Endpoints:
- GET  /sessions - List all sessions
- GET  /sessions/{id} - Get session details
- GET  /memory - Get longitudinal memory
- GET  /memory/search - Search memory
- GET  /memory/stats - Get memory statistics

Migrated from:
- backend/services/timeline/api/public/timeline.py
- backend/api/routers/memory/public/longitudinal_memory.py
"""

from __future__ import annotations
