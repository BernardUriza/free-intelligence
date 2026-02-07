"""Transcription Domain - Audio streaming and job management.

Sub-modules:
- streaming: Audio chunk upload, job status polling, session management

Endpoints (4 total):
- POST /stream - Upload audio chunk for transcription
- GET  /jobs/{session_id} - Poll transcription job status
- POST /end-session - Save full audio + webspeech transcripts
- GET  /sessions/{session_id}/chunks - Get all chunks for session

Features:
- Strategy Pattern for medical/chat transcription modes
- ChunkHandler abstraction for mode-specific workflows
- Audit logging for compliance tracking
- HDF5 storage for webspeech data (Triple Vision)

Migrated from: backend/api/routers/transcription/public/transcription.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import streaming

router = APIRouter()
router.include_router(streaming.router)
