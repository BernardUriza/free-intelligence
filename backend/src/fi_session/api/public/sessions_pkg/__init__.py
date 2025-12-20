from __future__ import annotations

from fastapi import APIRouter

from . import audio, audit, diarization, monitor, transcription_sources, workflows

router = APIRouter()
router.include_router(workflows.router)
router.include_router(monitor.router)
router.include_router(diarization.router)
router.include_router(transcription_sources.router)
router.include_router(audio.router)
router.include_router(audit.router)
