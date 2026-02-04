"""Session Infrastructure Module.

Provides session management endpoints for recording sessions.

Architecture:
- api/internal/sessions.py: Session CRUD operations
- api/internal/checkpoint.py: Incremental audio checkpoint
- api/internal/finalize.py: Session finalization + encryption

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/session/
"""
