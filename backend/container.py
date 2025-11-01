"""Dependency Injection container for Free Intelligence backend.

Centralizes creation and management of application dependencies.
Replaces global state with explicit dependency injection.

Clean Code Principles:
- Inversion of Control: Container manages object lifecycle
- Single Responsibility: Container only manages dependencies
- Testability: Easy to inject mock implementations for testing
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from backend.repositories import (
    AuditRepository,
    CorpusRepository,
    SessionRepository,
)
from backend.services import (
    AuditService,
    CorpusService,
    DiarizationService,
    ExportService,
    SessionService,
)

logger = logging.getLogger(__name__)


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

        self._corpus_service: Optional[CorpusService] = None
        self._session_service: Optional[SessionService] = None
        self._audit_service: Optional[AuditService] = None
        self._diarization_service: Optional[DiarizationService] = None
        self._export_service: Optional[ExportService] = None

        logger.info("DIContainer initialized", h5_file_path=str(self.h5_file_path))

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
                logger.info("CorpusRepository initialized")
            except OSError as e:
                logger.error("CORPUS_REPOSITORY_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize CorpusRepository: {e}") from e

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
                logger.info("SessionRepository initialized")
            except OSError as e:
                logger.error("SESSION_REPOSITORY_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize SessionRepository: {e}") from e

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
                logger.info("AuditRepository initialized")
            except OSError as e:
                logger.error("AUDIT_REPOSITORY_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize AuditRepository: {e}") from e

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
                logger.info("CorpusService initialized")
            except OSError as e:
                logger.error("CORPUS_SERVICE_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize CorpusService: {e}") from e

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
                logger.info("SessionService initialized")
            except OSError as e:
                logger.error("SESSION_SERVICE_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize SessionService: {e}") from e

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
                logger.info("AuditService initialized")
            except OSError as e:
                logger.error("AUDIT_SERVICE_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize AuditService: {e}") from e

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
                logger.info("DiarizationService initialized")
            except OSError as e:
                logger.error("DIARIZATION_SERVICE_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize DiarizationService: {e}") from e

        return self._diarization_service

    def get_export_service(self) -> ExportService:
        """Get or create ExportService singleton.

        Returns:
            ExportService instance

        Raises:
            IOError: If service initialization fails
        """
        if self._export_service is None:
            try:
                self._export_service = ExportService()
                logger.info("ExportService initialized")
            except OSError as e:
                logger.error("EXPORT_SERVICE_INIT_FAILED", error=str(e))
                raise IOError(f"Failed to initialize ExportService: {e}") from e

        return self._export_service

    def reset(self) -> None:
        """Reset all singletons (useful for testing).

        Closes all repositories and clears singleton references.
        """
        logger.info("Resetting DIContainer")

        self._corpus_repository = None
        self._session_repository = None
        self._audit_repository = None

        self._corpus_service = None
        self._session_service = None
        self._audit_service = None
        self._diarization_service = None
        self._export_service = None


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
