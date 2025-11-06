"""Dependency Injection container for Free Intelligence backend.

Centralizes creation and management of application dependencies.
Replaces global state with explicit dependency injection.

Clean Code Principles:
- Inversion of Control: Container manages object lifecycle
- Single Responsibility: Container only manages dependencies
- Testability: Easy to inject mock implementations for testing
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

# NOTE: Defer logger import to avoid circular dependency:
# backend.logger -> backend.common.logger -> backend.common.__init__ -> backend.common.container
# Logger is accessed via get_logger() function call below
from backend.repositories import AuditRepository, CorpusRepository, SessionRepository

# Type checking imports - Pylance uses these for type information
if TYPE_CHECKING:
    from backend.services import (
        AuditService,
        CorpusService,
        DiagnosticsService,
        DiarizationService,
        EvidenceService,
        ExportService,
        SessionService,
        SystemHealthService,
        TranscriptionService,
        TriageService,
    )
    from backend.services.diarization_job_service import DiarizationJobService
else:
    # Runtime imports - accessed via __getattr__ on services module
    def _import_service(name: str) -> Any:
        """Helper to import services at runtime, accessing via module __getattr__.

        Returns a stub if the service has unmet dependencies.
        """
        import backend.services as services

        try:
            return getattr(services, name)
        except AttributeError:
            # Service has unmet dependencies - return a stub class
            # Type information still comes from TYPE_CHECKING imports above
            return type(name, (), {})

    AuditService = _import_service("AuditService")  # type: ignore[assignment]
    CorpusService = _import_service("CorpusService")  # type: ignore[assignment]
    DiagnosticsService = _import_service("DiagnosticsService")  # type: ignore[assignment]
    DiarizationService = _import_service("DiarizationService")  # type: ignore[assignment]
    EvidenceService = _import_service("EvidenceService")  # type: ignore[assignment]
    ExportService = _import_service("ExportService")  # type: ignore[assignment]
    SessionService = _import_service("SessionService")  # type: ignore[assignment]
    SystemHealthService = _import_service("SystemHealthService")  # type: ignore[assignment]
    TranscriptionService = _import_service("TranscriptionService")  # type: ignore[assignment]
    TriageService = _import_service("TriageService")  # type: ignore[assignment]

    from backend.services.diarization_job_service import (
        DiarizationJobService,  # type: ignore[assignment]
    )


def _get_logger() -> Any:
    """Lazy logger initialization to avoid circular imports."""
    from backend.logger import get_logger

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
        self._corpus_repository: Optional[CorpusRepository] = None
        self._session_repository: Optional[SessionRepository] = None
        self._audit_repository: Optional[AuditRepository] = None

        self._audit_service: Optional[AuditService] = None
        self._corpus_service: Optional[CorpusService] = None
        self._diarization_service: Optional[DiarizationService] = None
        self._diarization_job_service: Optional[DiarizationJobService] = None
        self._diagnostics_service: Optional[DiagnosticsService] = None
        self._evidence_service: Optional[EvidenceService] = None
        self._export_service: Optional[ExportService] = None
        self._session_service: Optional[SessionService] = None
        self._system_health_service: Optional[SystemHealthService] = None
        self._transcription_service: Optional[TranscriptionService] = None
        self._triage_service: Optional[TriageService] = None

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
                _get_logger().error(f"CORPUS_REPOSITORY_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"SESSION_REPOSITORY_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"AUDIT_REPOSITORY_INIT_FAILED: {str(e)}")
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
                repository = self.get_corpus_repository()
                self._corpus_service = CorpusService(repository)
                _get_logger().info("CorpusService initialized")
            except OSError as e:
                _get_logger().error(f"CORPUS_SERVICE_INIT_FAILED: {str(e)}")
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
                repository = self.get_session_repository()
                self._session_service = SessionService(repository)
                _get_logger().info("SessionService initialized")
            except OSError as e:
                _get_logger().error(f"SESSION_SERVICE_INIT_FAILED: {str(e)}")
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
                repository = self.get_audit_repository()
                self._audit_service = AuditService(repository)
                _get_logger().info("AuditService initialized")
            except OSError as e:
                _get_logger().error(f"AUDIT_SERVICE_INIT_FAILED: {str(e)}")
                raise OSError(f"Failed to initialize AuditService: {e}") from e

        return self._audit_service

    def get_diarization_service(self) -> DiarizationService:
        """Get or create DiarizationService singleton.

        Returns:
            DiarizationService instance (with session and corpus services injected)

        Raises:
            IOError: If service initialization fails
        """
        if self._diarization_service is None:
            try:
                # Inject other services
                corpus_service = self.get_corpus_service()
                session_service = self.get_session_service()

                self._diarization_service = DiarizationService(
                    corpus_service=corpus_service,
                    session_service=session_service,
                )
                _get_logger().info("DiarizationService initialized")
            except OSError as e:
                _get_logger().error(f"DIARIZATION_SERVICE_INIT_FAILED: {str(e)}")
                raise OSError(f"Failed to initialize DiarizationService: {e}") from e

        return self._diarization_service

    def get_diarization_job_service(self) -> DiarizationJobService:
        """Get or create DiarizationJobService singleton.

        Returns:
            DiarizationJobService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._diarization_job_service is None:
            try:
                # Check if using low-priority worker
                import os

                use_lowprio = os.getenv("DIARIZATION_LOWPRIO", "true").lower() == "true"

                self._diarization_job_service = DiarizationJobService(use_lowprio=use_lowprio)
                _get_logger().info(
                    f"DiarizationJobService initialized with use_lowprio={use_lowprio}"
                )
            except OSError as e:
                _get_logger().error(f"DIARIZATION_JOB_SERVICE_INIT_FAILED: {str(e)}")
                raise OSError(f"Failed to initialize DiarizationJobService: {e}") from e

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
                _get_logger().error(f"EXPORT_SERVICE_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"TRANSCRIPTION_SERVICE_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"EVIDENCE_SERVICE_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"TRIAGE_SERVICE_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"SYSTEM_HEALTH_SERVICE_INIT_FAILED: {str(e)}")
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
                _get_logger().error(f"DIAGNOSTICS_SERVICE_INIT_FAILED: {str(e)}")
                raise OSError(f"Failed to initialize DiagnosticsService: {e}") from e

        return self._diagnostics_service

    def reset(self) -> None:
        """Reset all singletons (useful for testing).

        Closes all repositories and clears singleton references.
        """
        _get_logger().info("Resetting DIContainer")

        self._audit_repository = None
        self._corpus_repository = None
        self._session_repository = None

        self._audit_service = None
        self._corpus_service = None
        self._diarization_service = None
        self._diarization_job_service = None
        self._diagnostics_service = None
        self._evidence_service = None
        self._export_service = None
        self._session_service = None
        self._system_health_service = None
        self._transcription_service = None
        self._triage_service = None


# Global container instance (created on module import)
_global_container: Optional[DIContainer] = None


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
