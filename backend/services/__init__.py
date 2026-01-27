"""Services module - re-exports from backend.core.services and other locations.

This module provides backward compatibility for code that imports from backend.services.
"""

from __future__ import annotations

# Re-export services from their new locations
try:
    from backend.api.audit.services.audit_service import AuditService
except ImportError:
    AuditService = None  # type: ignore[assignment,misc]

try:
    from backend.core.infrastructure.storage.services.corpus_service import CorpusService
except ImportError:
    CorpusService = None  # type: ignore[assignment,misc]

try:
    from backend.utils.common.services.diagnostics_service import DiagnosticsService
except ImportError:
    DiagnosticsService = None  # type: ignore[assignment,misc]

try:
    from backend.core.services.transcription.services.diarization_service import (
        DiarizationJobService,
        DiarizationService,
    )
except ImportError:
    DiarizationService = None  # type: ignore[assignment,misc]
    DiarizationJobService = None  # type: ignore[assignment,misc]

try:
    from backend.utils.common.services.evidence_service import EvidenceService
except ImportError:
    EvidenceService = None  # type: ignore[assignment,misc]

try:
    from backend.utils.common.services.export_service import ExportService
except ImportError:
    ExportService = None  # type: ignore[assignment,misc]

try:
    from backend.core.domain.session.services.session_service import SessionService
except ImportError:
    SessionService = None  # type: ignore[assignment,misc]

try:
    from backend.utils.system.services.system_health_service import SystemHealthService
except ImportError:
    SystemHealthService = None  # type: ignore[assignment,misc]

try:
    from backend.core.services.transcription.services.transcription_service import TranscriptionService
except ImportError:
    TranscriptionService = None  # type: ignore[assignment,misc]

try:
    from backend.utils.common.services.triage_service import TriageService
except ImportError:
    TriageService = None  # type: ignore[assignment,misc]

__all__ = [
    "AuditService",
    "CorpusService",
    "DiagnosticsService",
    "DiarizationJobService",
    "DiarizationService",
    "EvidenceService",
    "ExportService",
    "SessionService",
    "SystemHealthService",
    "TranscriptionService",
    "TriageService",
]
