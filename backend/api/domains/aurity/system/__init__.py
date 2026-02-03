"""System Domain - Infrastructure metrics and management.

Endpoints:
- GET  /disk-usage - Get disk usage stats
- GET  /llm-status - Get LLM provider status
- POST /clear-memory - Clear memory cache
- GET  /kpis - Get system KPIs

Migrated from: backend/infrastructure/system/api/public/system.py
"""

from __future__ import annotations
