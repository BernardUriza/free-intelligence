"""Service layer for business logic.

Contains domain services that orchestrate repository operations
and implement business rules.

Clean Code Principles:
- Separation of Concerns: Business logic separated from persistence
- Single Responsibility: Each service handles one domain
- Dependency Injection: Services receive dependencies, don't create them
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type stubs for Pylance - used only during static analysis
    from backend.services.audit_service import AuditService
    from backend.services.corpus_service import CorpusService
    from backend.services.diagnostics_service import DiagnosticsService
    from backend.services.diarization_service import DiarizationService
    from backend.services.evidence_service import EvidenceService
    from backend.services.export_service import ExportService
    from backend.services.session_service import SessionService
    from backend.services.system_health_service import SystemHealthService
    from backend.services.transcription_service import TranscriptionService
    from backend.services.triage_service import TriageService


def __getattr__(name: str) -> Any:
    """Lazy load services to prevent circular imports at runtime.

    Pylance uses TYPE_CHECKING imports above for type information,
    so type checking works even though this lazy loading is used at runtime.

    Gracefully handles import errors by raising AttributeError for missing services.
    """
    try:
        if name == "AuditService":
            from backend.services.audit_service import AuditService

            return AuditService
        elif name == "CorpusService":
            from backend.services.corpus_service import CorpusService

            return CorpusService
        elif name == "DiagnosticsService":
            from backend.services.diagnostics_service import DiagnosticsService

            return DiagnosticsService
        elif name == "DiarizationService":
            from backend.services.diarization_service import DiarizationService

            return DiarizationService
        elif name == "EvidenceService":
            try:
                from backend.services.evidence_service import EvidenceService

                return EvidenceService
            except ModuleNotFoundError:
                # EvidenceService has unmet dependencies, but type stubs still work
                raise AttributeError(
                    "EvidenceService unavailable: missing dependency (backend.evidence_pack)"
                ) from None
        elif name == "ExportService":
            from backend.services.export_service import ExportService

            return ExportService
        elif name == "SessionService":
            from backend.services.session_service import SessionService

            return SessionService
        elif name == "SystemHealthService":
            from backend.services.system_health_service import SystemHealthService

            return SystemHealthService
        elif name == "TranscriptionService":
            from backend.services.transcription_service import TranscriptionService

            return TranscriptionService
        elif name == "TriageService":
            from backend.services.triage_service import TriageService

            return TriageService
    except AttributeError:
        raise
    except Exception as e:
        # Catch unexpected errors and convert to AttributeError
        raise AttributeError(f"Error loading {name}: {e}") from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuditService",
    "CorpusService",
    "DiagnosticsService",
    "DiarizationService",
    "EvidenceService",
    "ExportService",
    "SessionService",
    "SystemHealthService",
    "TranscriptionService",
    "TriageService",
]
