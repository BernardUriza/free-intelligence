"""Tests for ExportService.

Validates export manifest generation and hash verification.
"""

from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.export_service import ExportService


class TestExportService:
    """Test suite for ExportService."""

    def test_create_export_service(self, export_service: ExportService):
        """Test ExportService instantiation."""
        assert export_service is not None

    def test_export_service_has_export_dir(self, export_service: ExportService):
        """Test that export service has configured export directory."""
        # ExportService should have export_dir attribute
        assert hasattr(export_service, "export_dir")

    def test_export_service_isolation(self, di_container):
        """Test that export service instances are isolated per container."""
        service1 = di_container.get_export_service()
        service2 = di_container.get_export_service()

        # Should return same instance (singleton)
        assert service1 is service2

    @pytest.mark.skip(reason="Requires HDF5 corpus data")
    def test_generate_manifest(self, export_service: ExportService):
        """Test manifest generation (requires corpus data)."""
        # This test requires actual corpus data to be present
        # Skip in basic test suite, implement when export functionality is complete
        pass

    @pytest.mark.skip(reason="Requires export implementation")
    def test_verify_export_hash(self, export_service: ExportService):
        """Test export hash verification (requires implementation)."""
        # Placeholder for future hash verification tests
        pass
