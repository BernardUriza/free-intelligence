"""Medical AI Domain - Core medical workflow for AURITY telemedicine.

This domain handles the complete AI-powered medical consultation workflow:
- Session workflows (diarization, SOAP notes, emotion analysis)
- Real-time progress monitoring
- Diarization segment management
- Audio file retrieval
- Transcription source management
- Doctor audit and feedback

Endpoints (when connected to router):
- POST /sessions/{id}/diarization - Start speaker diarization
- POST /sessions/{id}/soap - Generate SOAP note
- POST /sessions/{id}/emotion - Analyze emotions
- POST /sessions/{id}/analyze - Intelligent workflow orchestration
- POST /sessions/{id}/finalize - Finalize session
- POST /sessions/{id}/checkpoint - Save partial progress
- GET  /sessions/{id}/monitor - Real-time progress monitoring
- GET  /sessions/{id}/diarization/segments - Get diarization segments
- PATCH /sessions/{id}/diarization/segments/{idx} - Update segment
- POST /sessions/{id}/diarization/import - Import external diarization
- GET  /diarization/jobs/{job_id} - Poll diarization job status
- GET  /sessions/{id}/audio - Download session audio
- GET  /sessions/{id}/transcription-sources - Get all transcription sources
- GET  /sessions/{id}/audit - Get session audit data
- POST /sessions/{id}/feedback - Submit doctor feedback

Migrated from: backend/api/routers/session/public/sessions_pkg/
"""

from __future__ import annotations

from fastapi import APIRouter

from . import workflows, monitor, diarization, audio, transcription_sources, audit

router = APIRouter()
router.include_router(workflows.router)
router.include_router(monitor.router)
router.include_router(diarization.router)
router.include_router(transcription_sources.router)
router.include_router(audio.router)
router.include_router(audit.router)

__all__ = [
    "router",
    "workflows",
    "monitor",
    "diarization",
    "audio",
    "transcription_sources",
    "audit",
]
