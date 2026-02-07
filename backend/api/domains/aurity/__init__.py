"""AURITY App Namespace - Advanced Universal Reliable Intelligence for Telemedicine Yield.

All public endpoints for the AURITY telemedicine app live under /api/aurity/.

Domains:
- medical_ai: Core medical workflow (sessions, diarization, SOAP, emotion)
- clinic: Clinic-specific features (TV content, waiting room, widgets, media)
- transcription: Audio streaming and job management
- assistant: AI chat with configurable personas
- prescriptions: Medication catalog, interactions, allergies
- timeline: Session history and longitudinal memory
- knowledge_base: Document upload and RAG-powered search
- system: Infrastructure metrics (disk, memory, LLM status)
"""

from __future__ import annotations
