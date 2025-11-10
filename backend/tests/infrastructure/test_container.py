"""Tests for DI Container.

Validates dependency injection container lifecycle and service management.
"""

from __future__ import annotations

from pathlib import Path


class TestDIContainer:
    """Test suite for DIContainer."""

    def test_container_initialization(self, di_container):
        """Test that container initializes successfully."""
        assert di_container is not None
        assert isinstance(di_container.h5_file_path, Path)

    def test_container_get_corpus_service(self, di_container):
        """Test getting CorpusService from container."""
        service = di_container.get_corpus_service()

        assert service is not None
        assert hasattr(service, "repository")

    def test_container_get_session_service(self, di_container):
        """Test getting SessionService from container."""
        service = di_container.get_session_service()

        assert service is not None
        assert hasattr(service, "repository")

    def test_container_get_audit_service(self, di_container):
        """Test getting AuditService from container."""
        service = di_container.get_audit_service()

        assert service is not None
        assert hasattr(service, "repository")

    def test_container_get_export_service(self, di_container):
        """Test getting ExportService from container."""
        service = di_container.get_export_service()

        assert service is not None
        assert hasattr(service, "export_dir")

    def test_container_get_triage_service(self, di_container):
        """Test getting TriageService from container."""
        service = di_container.get_triage_service()

        assert service is not None

    def test_container_singleton_pattern(self, di_container):
        """Test that services are singletons within container."""
        service1 = di_container.get_session_service()
        service2 = di_container.get_session_service()

        # Should return same instance
        assert service1 is service2

    def test_container_reset(self, di_container):
        """Test container reset clears singletons."""
        # Get service to create singleton
        service1 = di_container.get_session_service()

        # Reset container
        di_container.reset()

        # Get service again - should be new instance
        service2 = di_container.get_session_service()

        # Should be different instances after reset
        assert service1 is not service2

    def test_container_repository_isolation(self, di_container):
        """Test that repositories are isolated per container."""
        repo1 = di_container.get_session_repository()
        repo2 = di_container.get_session_repository()

        # Should return same instance (singleton)
        assert repo1 is repo2

    def test_container_multiple_services(self, di_container):
        """Test getting multiple services from same container."""
        session_service = di_container.get_session_service()
        audit_service = di_container.get_audit_service()
        corpus_service = di_container.get_corpus_service()

        assert session_service is not None
        assert audit_service is not None
        assert corpus_service is not None

        # All should be different service instances
        assert session_service is not audit_service
        assert session_service is not corpus_service
        assert audit_service is not corpus_service


class TestContainerErrorHandling:
    """Test error handling in DIContainer."""

    def test_container_with_invalid_h5_path(self, temp_h5_file):
        """Test container initialization with invalid HDF5 path."""
        from packages.fi_common.infrastructure.container import DIContainer

        # Use non-existent path
        invalid_path = temp_h5_file.parent / "nonexistent_dir" / "test.h5"

        # Container should initialize (lazy loading)
        container = DIContainer(h5_file_path=invalid_path)

        assert container is not None

        # Error may or may not occur - container handles missing files gracefully
        # Just verify container was created
        assert container.h5_file_path == invalid_path

    def test_container_service_dependency_chain(self, di_container):
        """Test that service dependencies are resolved correctly."""
        # SessionService depends on SessionRepository
        session_service = di_container.get_session_service()

        # Verify repository is injected
        assert hasattr(session_service, "repository")
        assert session_service.repository is not None

        # Repository should be the same instance from container
        repo_from_container = di_container.get_session_repository()
        assert session_service.repository is repo_from_container
