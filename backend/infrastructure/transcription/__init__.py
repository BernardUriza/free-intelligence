"""Transcription Infrastructure Module.

Provides transcription and diarization endpoints.

Architecture:
- api/internal/transcribe.py: Audio chunk upload + transcription job status
- api/internal/diarization.py: Diarization job status polling

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/transcription/
"""
