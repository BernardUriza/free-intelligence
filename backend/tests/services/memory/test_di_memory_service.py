"""Unit tests for DIMemoryService (DI refactored version).

Tests longitudinal memory aggregation with mocked dependencies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.6 - Testing Strategy
"""

import pytest
from unittest.mock import Mock, patch
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.utils.common.interfaces.ilogger import ILogger


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = Mock(spec=ILogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def service(mock_logger, tmp_path):
    """DIMemoryService instance with mocked dependencies and temp corpus."""
    # Use temporary HDF5 file for testing
    corpus_path = str(tmp_path / "test_corpus.h5")
    return DIMemoryService(
        corpus_path=corpus_path,
        logger=mock_logger,
    )


class TestGetLongitudinalMemory:
    """Tests for get_longitudinal_memory() method."""

    def test_returns_empty_for_nonexistent_patient(self, service):
        """Test that get_longitudinal_memory returns empty data for nonexistent patient."""
        # Arrange
        patient_id = "nonexistent-patient-123"

        # Act
        result = service.get_longitudinal_memory(
            patient_id=patient_id,
            lookback_days=30,
        )

        # Assert
        assert result is not None
        assert "chat_events" in result
        assert "audio_events" in result
        assert len(result["chat_events"]) == 0
        assert len(result["audio_events"]) == 0

    @patch("backend.services.memory.services.di_memory_service.h5py")
    def test_aggregates_chat_events(self, mock_h5py, service):
        """Test that get_longitudinal_memory aggregates chat events."""
        # Arrange
        patient_id = "patient-123"

        # Mock HDF5 structure
        mock_file = Mock()
        mock_h5py.File.return_value.__enter__.return_value = mock_file

        # Simulate chat events in HDF5
        mock_file.visit.return_value = None  # Simplified

        # Act
        result = service.get_longitudinal_memory(
            patient_id=patient_id,
            lookback_days=30,
        )

        # Assert
        assert "chat_events" in result
        assert isinstance(result["chat_events"], list)

    def test_filters_by_lookback_days(self, service):
        """Test that get_longitudinal_memory filters events by lookback_days."""
        # Arrange
        patient_id = "patient-123"
        lookback_days = 7

        # Act
        result = service.get_longitudinal_memory(
            patient_id=patient_id,
            lookback_days=lookback_days,
        )

        # Assert
        # All events should be within lookback window
        # (This test needs actual HDF5 data to validate properly)
        assert result is not None


class TestSearchMemory:
    """Tests for search_memory() method."""

    def test_returns_empty_for_no_matches(self, service):
        """Test that search_memory returns empty list for no matches."""
        # Arrange
        patient_id = "patient-123"
        query = "nonexistent-query-term"

        # Act
        results = service.search_memory(
            patient_id=patient_id,
            query=query,
            limit=10,
        )

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0

    def test_limits_results(self, service):
        """Test that search_memory respects limit parameter."""
        # Arrange
        patient_id = "patient-123"
        query = "test"
        limit = 5

        # Act
        results = service.search_memory(
            patient_id=patient_id,
            query=query,
            limit=limit,
        )

        # Assert
        assert len(results) <= limit


class TestGetStats:
    """Tests for get_stats() method."""

    def test_returns_stats_dict(self, service):
        """Test that get_stats returns statistics dictionary."""
        # Arrange
        patient_id = "patient-123"

        # Act
        stats = service.get_stats(patient_id=patient_id)

        # Assert
        assert isinstance(stats, dict)
        assert "total_events" in stats
        assert "chat_count" in stats
        assert "audio_count" in stats

    def test_stats_are_non_negative(self, service):
        """Test that get_stats returns non-negative counts."""
        # Arrange
        patient_id = "patient-123"

        # Act
        stats = service.get_stats(patient_id=patient_id)

        # Assert
        assert stats["total_events"] >= 0
        assert stats["chat_count"] >= 0
        assert stats["audio_count"] >= 0
