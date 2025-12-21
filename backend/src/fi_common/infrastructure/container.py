"""Dependency Injection container for Free Intelligence backend.

Centralizes creation and management of application dependencies.
Replaces global state with explicit dependency injection.

Clean Code Principles:
- Inversion of Control: Container manages object lifecycle
- Single Responsibility: Container only manages dependencies
- Testability: Easy to inject mock implementations for testing
"""

from __future__ import annotations

from backend.src.fi_common.interfaces.ievent_bus import IEventBus

# Import interfaces and implementations for DI
from backend.src.fi_common.interfaces.ilogger import ILogger
from backend.src.fi_common.interfaces.itask_repository import ITaskRepository

# NOTE: HDF5TaskRepository was removed during fi_coder refactor
# Using adapter that wraps functional task_repository module
from backend.src.fi_common.utils.event_bus import InMemoryEventBus
from backend.src.fi_common.utils.structured_logger import StructuredLogger
from backend.src.fi_common.utils.task_repository_adapter import TaskRepositoryAdapter
from pathlib import Path
from typing import TYPE_CHECKING, Any

# NOTE: Defer logger import to avoid circular dependency:
# backend.logger -> backend.src.logger -> backend.src.__init__ -> backend.src.fi_common.infrastructure.container
# Logger is accessed via get_logger() function call below
from backend.repositories import AuditRepository, CorpusRepository, SessionRepository

# Type checking imports - Pylance uses these for type information
if TYPE_CHECKING:
    from backend.src.fi_audit.services.audit_service import AuditService
    from backend.src.fi_coder.services.session_service import SessionService as DISessionService
    from backend.src.fi_common.services.diagnostics_service import DiagnosticsService
    from backend.src.fi_common.services.evidence_service import EvidenceService
    from backend.src.fi_common.services.export_service import ExportService
    from backend.src.fi_common.services.triage_service import TriageService
    from backend.src.fi_session.services.session_service import SessionService
    from backend.src.fi_storage.services.corpus_service import CorpusService
    from backend.src.fi_system.services.system_health_service import SystemHealthService
    from backend.src.fi_transcription.services.diarization_service import (
        DiarizationJobService,
        DiarizationService,
    )
    from backend.src.fi_transcription.services.transcription_service import TranscriptionService
else:
    # Runtime imports - accessed via __getattr__ on services module
    def _import_service(name: str) -> Any:
        """Helper to import services at runtime, accessing via module __getattr__.

        Returns a stub if the service has unmet dependencies or import fails.
        """
        try:
            import backend.services as services
            return getattr(services, name)
        except (ImportError, AttributeError):
            # Service has unmet dependencies or module import failed - return a stub class
            # Type information still comes from TYPE_CHECKING imports above
            return type(name, (), {})

    AuditService = _import_service("AuditService")  # type: ignore[assignment]
    CorpusService = _import_service("CorpusService")  # type: ignore[assignment]
    DiagnosticsService = _import_service("DiagnosticsService")  # type: ignore[assignment]
    DiarizationService = _import_service("DiarizationService")  # type: ignore[assignment]
    DiarizationJobService = _import_service("DiarizationJobService")  # type: ignore[assignment]
    EvidenceService = _import_service("EvidenceService")  # type: ignore[assignment]
    ExportService = _import_service("ExportService")  # type: ignore[assignment]
    SessionService = _import_service("SessionService")  # type: ignore[assignment]
    SystemHealthService = _import_service("SystemHealthService")  # type: ignore[assignment]
    TranscriptionService = _import_service("TranscriptionService")  # type: ignore[assignment]
    TriageService = _import_service("TriageService")  # type: ignore[assignment]

    # Import DI services
    from backend.src.fi_audit.services.di_audit_service import DIAuditService
    from backend.src.fi_evidence.services.evidence_service import DIEvidenceService
    from backend.src.fi_export.services.export_service import DIExportService
    from backend.src.fi_session.services.di_session_service import (
        SessionService as DISessionService,
    )
    from backend.src.fi_system.services.di_system_health_service import DISystemHealthService
    from backend.src.fi_transcription.services.di_transcription_service import (
        DITranscriptionService,
    )


def _get_logger() -> Any:
    """Lazy logger initialization to avoid circular imports."""
    from backend.src.fi_common.logging.logger import get_logger

    return get_logger(__name__)


class DIContainer:
    """Dependency Injection container for application services.

    Manages creation and lifecycle of repositories and services.
    Prevents global state by explicitly managing all dependencies.

    Usage:
        container = DIContainer(h5_file_path="storage/corpus.h5")
        corpus_service = container.get_corpus_service()
    """

    def __init__(self, h5_file_path: str | Path = "storage/corpus.h5") -> None:
        """Initialize DI container with database path.

        Args:
            h5_file_path: Path to HDF5 database file
        """
        self.h5_file_path = Path(h5_file_path)

        # Lazy-loaded singletons (created on first access)
        self._corpus_repository: CorpusRepository | None = None
        self._session_repository: SessionRepository | None = None
        self._audit_repository: AuditRepository | None = None

        # DI dependencies
        self._logger: ILogger | None = None
        self._task_repository: ITaskRepository | None = None
        self._event_bus: IEventBus | None = None

        self._audit_service: AuditService | None = None
        self._corpus_service: CorpusService | None = None
        self._diarization_service: DiarizationService | None = None
        self._diarization_job_service: DiarizationJobService | None = None
        self._diagnostics_service: DiagnosticsService | None = None
        self._evidence_service: EvidenceService | None = None
        self._export_service: ExportService | None = None
        self._session_service: SessionService | None = None
        self._di_session_service: DISessionService | None = None
        self._di_audit_service: DIAuditService | None = None
        self._di_system_health_service: DISystemHealthService | None = None
        self._di_transcription_service: DITranscriptionService | None = None
        self._di_evidence_service: DIEvidenceService | None = None
        self._di_export_service: DIExportService | None = None
        self._system_health_service: SystemHealthService | None = None
        self._transcription_service: TranscriptionService | None = None
        self._triage_service: TriageService | None = None

        _get_logger().info(f"DIContainer initialized with h5_file_path={self.h5_file_path}")

    # Repositories

    def get_corpus_repository(self) -> CorpusRepository:
        """Get or create CorpusRepository singleton.

        Returns:
            CorpusRepository instance

        Raises:
            IOError: If repository initialization fails
        """
        if self._corpus_repository is None:
            try:
                self._corpus_repository = CorpusRepository(self.h5_file_path)
                _get_logger().info("CorpusRepository initialized")
            except OSError as e:
                _get_logger().error(f"CORPUS_REPOSITORY_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize CorpusRepository: {e}") from e

        return self._corpus_repository

    def get_session_repository(self) -> SessionRepository:
        """Get or create SessionRepository singleton.

        Returns:
            SessionRepository instance

        Raises:
            IOError: If repository initialization fails
        """
        if self._session_repository is None:
            try:
                self._session_repository = SessionRepository(self.h5_file_path)
                _get_logger().info("SessionRepository initialized")
            except OSError as e:
                _get_logger().error(f"SESSION_REPOSITORY_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize SessionRepository: {e}") from e

        return self._session_repository

    def get_audit_repository(self) -> AuditRepository:
        """Get or create AuditRepository singleton.

        Returns:
            AuditRepository instance

        Raises:
            IOError: If repository initialization fails
        """
        if self._audit_repository is None:
            try:
                self._audit_repository = AuditRepository(self.h5_file_path)
                _get_logger().info("AuditRepository initialized")
            except OSError as e:
                _get_logger().error(f"AUDIT_REPOSITORY_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize AuditRepository: {e}") from e

        return self._audit_repository

    # Services

    def get_corpus_service(self) -> CorpusService:
        """Get or create CorpusService singleton.

        Returns:
            CorpusService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._corpus_service is None:
            try:
                corpus_repository: CorpusRepository = self.get_corpus_repository()
                self._corpus_service = CorpusService(corpus_repository)
                _get_logger().info("CorpusService initialized")
            except OSError as e:
                _get_logger().error(f"CORPUS_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize CorpusService: {e}") from e

        return self._corpus_service

    def get_session_service(self) -> SessionService:
        """Get or create SessionService singleton.

        Returns:
            SessionService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._session_service is None:
            try:
                session_repository: SessionRepository = self.get_session_repository()
                self._session_service = SessionService(session_repository)
                _get_logger().info("SessionService initialized")
            except OSError as e:
                _get_logger().error(f"SESSION_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize SessionService: {e}") from e

        return self._session_service

    def get_audit_service(self) -> AuditService:
        """Get or create AuditService singleton.

        Returns:
            AuditService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._audit_service is None:
            try:
                audit_repository: AuditRepository = self.get_audit_repository()
                self._audit_service = AuditService(audit_repository)
                _get_logger().info("AuditService initialized")
            except OSError as e:
                _get_logger().error(f"AUDIT_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize AuditService: {e}") from e

        return self._audit_service

    def get_diarization_service(self) -> DiarizationService:
        """Get or create DiarizationService singleton.

        Returns:
            DiarizationService instance (post-processing only, no dependencies)

        Raises:
            IOError: If service initialization fails
        """
        if self._diarization_service is None:
            try:
                # DiarizationService (refactored 2025-11-05) is post-processing only
                # It does NOT need corpus_service or session_service injected
                # It only classifies speakers and improves text on pre-transcribed segments
                self._diarization_service = DiarizationService()
                _get_logger().info("DiarizationService initialized")
            except OSError as e:
                _get_logger().error(f"DIARIZATION_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DiarizationService: {e}") from e

        return self._diarization_service

    def get_diarization_job_service(self) -> DiarizationJobService | None:
        """Get or create DiarizationJobService singleton.

        Returns:
            DiarizationJobService instance or None if initialization fails

        Raises:
            IOError: If service initialization fails
        """
        if self._diarization_job_service is None:
            try:
                import os

                from backend.src.fi_common.services.diarization.job_service import (
                    DiarizationJobService,
                )

                hdf5_path = os.getenv("AURITY_DIARIZATION_HDF5", "storage/diarization.h5")
                persist = os.getenv(
                    "AURITY_DIARIZATION_PERSIST_RESOLVED_STATUS", "false"
                ).lower() in {
                    "1",
                    "true",
                    "yes",
                }

                self._diarization_job_service = DiarizationJobService(
                    hdf5_path=hdf5_path, persist_resolved=persist
                )
                _get_logger().info("DiarizationJobService initialized")
            except Exception as e:
                _get_logger().error(f"DIARIZATION_JOB_SERVICE_INIT_FAILED: {e!s}")
                # Don't raise - return None for graceful degradation
                self._diarization_job_service = None

        return self._diarization_job_service

    def get_export_service(self) -> ExportService:
        """Get or create ExportService singleton.

        Returns:
            ExportService instance with default configuration

        Raises:
            IOError: If service initialization fails
        """
        if self._export_service is None:
            try:
                # ExportService takes optional parameters, using defaults (export_dir, signing_key, git_commit)
                self._export_service = ExportService(
                    export_dir=None,  # Will use $EXPORT_DIR env var or /tmp/fi_exports
                    signing_key=None,  # No signing key in MVP
                    git_commit="dev",  # Default commit hash
                )
                _get_logger().info("ExportService initialized")
            except OSError as e:
                _get_logger().error(f"EXPORT_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize ExportService: {e}") from e

        return self._export_service

    def get_transcription_service(self) -> TranscriptionService:
        """Get or create TranscriptionService singleton.

        Returns:
            TranscriptionService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._transcription_service is None:
            try:
                self._transcription_service = TranscriptionService()
                _get_logger().info("TranscriptionService initialized")
            except OSError as e:
                _get_logger().error(f"TRANSCRIPTION_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize TranscriptionService: {e}") from e

        return self._transcription_service

    def get_evidence_service(self) -> EvidenceService:
        """Get or create EvidenceService singleton.

        Returns:
            EvidenceService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._evidence_service is None:
            try:
                self._evidence_service = EvidenceService()
                _get_logger().info("EvidenceService initialized")
            except OSError as e:
                _get_logger().error(f"EVIDENCE_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize EvidenceService: {e}") from e

        return self._evidence_service

    def get_triage_service(self) -> TriageService:
        """Get or create TriageService singleton.

        Returns:
            TriageService instance with default data directory

        Raises:
            IOError: If service initialization fails
        """
        if self._triage_service is None:
            try:
                # TriageService takes optional data_dir parameter, using default from env or ./data/triage_buffers
                self._triage_service = TriageService(data_dir=None)
                _get_logger().info("TriageService initialized")
            except OSError as e:
                _get_logger().error(f"TRIAGE_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize TriageService: {e}") from e

        return self._triage_service

    def get_system_health_service(self) -> SystemHealthService:
        """Get or create SystemHealthService singleton.

        Returns:
            SystemHealthService instance

        Raises:
            OSError: If service initialization fails
        """
        if self._system_health_service is None:
            try:
                self._system_health_service = SystemHealthService()
                _get_logger().info("SystemHealthService initialized")
            except OSError as e:
                _get_logger().error(f"SYSTEM_HEALTH_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize SystemHealthService: {e}") from e

        return self._system_health_service

    def get_diagnostics_service(self) -> DiagnosticsService:
        """Get or create DiagnosticsService singleton.

        Returns:
            DiagnosticsService instance

        Raises:
            OSError: If service initialization fails
        """
        if self._diagnostics_service is None:
            try:
                self._diagnostics_service = DiagnosticsService()
                _get_logger().info("DiagnosticsService initialized")
            except OSError as e:
                _get_logger().error(f"DIAGNOSTICS_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DiagnosticsService: {e}") from e

        return self._diagnostics_service

    def get_logger(self) -> ILogger:
        """Get or create ILogger singleton.

        Returns:
            ILogger instance
        """
        if self._logger is None:
            self._logger = StructuredLogger()
            _get_logger().info("ILogger (StructuredLogger) initialized")
        return self._logger

    def get_task_repository(self) -> ITaskRepository:
        """Get or create ITaskRepository singleton.

        Returns:
            ITaskRepository instance

        Raises:
            IOError: If repository initialization fails
        """
        if self._task_repository is None:
            try:
                self._task_repository = TaskRepositoryAdapter(self.h5_file_path)
                _get_logger().info("ITaskRepository (TaskRepositoryAdapter) initialized")
            except OSError as e:
                _get_logger().error(f"TASK_REPOSITORY_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize ITaskRepository: {e}") from e
        return self._task_repository

    def get_event_bus(self) -> IEventBus:
        """Get or create IEventBus singleton.

        Returns:
            IEventBus instance
        """
        if self._event_bus is None:
            self._event_bus = InMemoryEventBus()
            _get_logger().info("IEventBus (InMemoryEventBus) initialized")
        return self._event_bus

    def get_di_session_service(self) -> DISessionService:
        """Get or create DI SessionService singleton with injected dependencies.

        Returns:
            DISessionService instance with ILogger and ITaskRepository injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_session_service is None:
            try:
                logger: ILogger = self.get_logger()
                task_repository: ITaskRepository = self.get_task_repository()
                event_bus: IEventBus = self.get_event_bus()
                self._di_session_service = DISessionService(logger, task_repository, event_bus)
                _get_logger().info("DISessionService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_SESSION_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DISessionService: {e}") from e

        return self._di_session_service

    def get_di_audit_service(self) -> DIAuditService:
        """Get or create DI AuditService singleton with injected dependencies.

        Returns:
            DIAuditService instance with ILogger and AuditRepository injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_audit_service is None:
            try:
                logger: ILogger = self.get_logger()
                audit_repository: AuditRepository = self.get_audit_repository()
                self._di_audit_service = DIAuditService(logger, audit_repository)
                _get_logger().info("DIAuditService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_AUDIT_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DIAuditService: {e}") from e

        return self._di_audit_service

    def get_di_system_health_service(self) -> DISystemHealthService:
        """Get or create DI SystemHealthService singleton with injected dependencies.

        Returns:
            DISystemHealthService instance with ILogger injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_system_health_service is None:
            try:
                logger: ILogger = self.get_logger()
                self._di_system_health_service = DISystemHealthService(logger)
                _get_logger().info("DISystemHealthService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_SYSTEM_HEALTH_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DISystemHealthService: {e}") from e

        return self._di_system_health_service

    def get_di_transcription_service(self) -> DITranscriptionService:
        """Get or create DI TranscriptionService singleton with injected dependencies.

        Returns:
            DITranscriptionService instance with ILogger and ITaskRepository injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_transcription_service is None:
            try:
                logger: ILogger = self.get_logger()
                task_repository: ITaskRepository = self.get_task_repository()
                self._di_transcription_service = DITranscriptionService(logger, task_repository)
                _get_logger().info("DITranscriptionService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_TRANSCRIPTION_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DITranscriptionService: {e}") from e

        return self._di_transcription_service

    def get_di_evidence_service(self) -> DIEvidenceService:
        """Get or create DI EvidenceService singleton with injected dependencies.

        Returns:
            DIEvidenceService instance with ILogger injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_evidence_service is None:
            try:
                logger: ILogger = self.get_logger()
                self._di_evidence_service = DIEvidenceService(logger)
                _get_logger().info("DIEvidenceService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_EVIDENCE_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DIEvidenceService: {e}") from e

        return self._di_evidence_service

    def get_di_export_service(self) -> DIExportService:
        """Get or create DI ExportService singleton with injected dependencies.

        Returns:
            DIExportService instance with ILogger injected

        Raises:
            IOError: If service initialization fails
        """
        if self._di_export_service is None:
            try:
                logger: ILogger = self.get_logger()
                self._di_export_service = DIExportService(logger)
                _get_logger().info("DIExportService initialized with DI")
            except OSError as e:
                _get_logger().error(f"DI_EXPORT_SERVICE_INIT_FAILED: {e!s}")
                raise OSError(f"Failed to initialize DIExportService: {e}") from e

        return self._di_export_service

    def reset(self) -> None:
        """Reset all singletons (useful for testing).

        Closes all repositories and clears singleton references.
        """
        _get_logger().info("Resetting DIContainer")

        self._audit_repository = None
        self._corpus_repository = None
        self._session_repository = None

        # DI dependencies
        self._logger = None
        self._task_repository = None
        self._event_bus = None

        self._audit_service = None
        self._corpus_service = None
        self._diarization_service = None
        self._diarization_job_service = None
        self._diagnostics_service = None
        self._evidence_service = None
        self._export_service = None
        self._session_service = None
        self._di_session_service = None
        self._di_audit_service = None
        self._di_system_health_service = None
        self._di_transcription_service = None
        self._di_evidence_service = None
        self._di_export_service = None
        self._system_health_service = None
        self._transcription_service = None
        self._triage_service = None


# Global container instance (created on module import)
_global_container: DIContainer | None = None


def get_container(
    h5_file_path: str | Path = "storage/corpus.h5",
) -> DIContainer:
    """Get or create global DI container.

    Args:
        h5_file_path: Path to HDF5 database file

    Returns:
        Global DIContainer instance

    Note:
        First call sets the h5_file_path. Subsequent calls return the
        same instance with the original h5_file_path.
    """
    global _global_container

    if _global_container is None:
        _global_container = DIContainer(h5_file_path)

    return _global_container


def reset_container() -> None:
    """Reset global container (for testing)."""
    global _global_container

    if _global_container:
        _global_container.reset()

    _global_container = None


# Alias for backward compatibility
Container = DIContainer
