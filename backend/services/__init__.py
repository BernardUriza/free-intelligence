"""Service layer for business logic.

Contains domain services that orchestrate repository operations
and implement business rules.

Clean Code Principles:
- Separation of Concerns: Business logic separated from persistence
- Single Responsibility: Each service handles one domain
- Dependency Injection: Services receive dependencies, don't create them
"""

from __future__ import annotations


# Lazy imports to prevent circular dependencies
def __getattr__(name: str):
    """Lazy load services to prevent circular imports."""
    try:
        if name == "AuditService":
            from backend.services.audit_service import AuditService

            return AuditService
        elif name == "CorpusService":
            try:
                from backend.services.corpus_service import CorpusService

                return CorpusService
            except ImportError:
                # Return a stub if not available
                return type("CorpusService", (), {})
        elif name == "DiagnosticsService":
            try:
                from backend.services.diagnostics_service import DiagnosticsService

                return DiagnosticsService
            except ImportError:
                return type("DiagnosticsService", (), {})
        elif name == "DiarizationService":
            # DiarizationService is a custom class, try different modules
            try:
                from backend.services.diarization_service_v2 import DiarizationService

                return DiarizationService
            except ImportError:
                try:
                    from backend.services.diarization_service import DiarizationService

                    return DiarizationService
                except (ImportError, AttributeError):
                    # Return stub class
                    return type("DiarizationService", (), {})
        elif name == "EvidenceService":
            try:
                from backend.services.evidence_service import EvidenceService

                return EvidenceService
            except ImportError:
                return type("EvidenceService", (), {})
        elif name == "ExportService":
            try:
                from backend.services.export_service import ExportService

                return ExportService
            except ImportError:
                return type("ExportService", (), {})
        elif name == "SessionService":
            try:
                from backend.services.session_service import SessionService

                return SessionService
            except ImportError:
                return type("SessionService", (), {})
        elif name == "SystemHealthService":
            try:
                from backend.services.system_health_service import SystemHealthService

                return SystemHealthService
            except ImportError:
                return type("SystemHealthService", (), {})
        elif name == "TranscriptionService":
            try:
                from backend.services.transcription_service import TranscriptionService

                return TranscriptionService
            except ImportError:
                return type("TranscriptionService", (), {})
        elif name == "TriageService":
            try:
                from backend.services.triage_service import TriageService

                return TriageService
            except ImportError:
                return type("TriageService", (), {})
    except Exception:
        pass
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
