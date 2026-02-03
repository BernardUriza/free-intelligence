"""Transcription Domain - Audio streaming and job management.

Endpoints:
- POST /stream - Start audio streaming for transcription
- GET  /jobs/{id} - Get transcription job status
- GET  /diarization/jobs/{id} - Get diarization job status

Migrated from: backend/api/routers/transcription/public/transcription.py
"""

from __future__ import annotations
