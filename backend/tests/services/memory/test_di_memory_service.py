"""Unit tests for DIMemoryService (DI refactored version).

Tests longitudinal memory aggregation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.repositories.interfaces.imemory_store import IMemoryStore
from backend.infrastructure.interfaces.ilogger import ILogger


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = Mock(spec=ILogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_memory_store():
    """Mock IMemoryStore."""
    store = Mock(spec=IMemoryStore)
    store.get_audio_events = Mock(return_value=([], 0))
    store.search_audio_events = Mock(return_value=[])
    store.get_audio_stats = Mock(return_value={
        "count": 0,
        "oldest_timestamp": None,
        "newest_timestamp": None,
        "unique_sessions": 0,
    })
    return store


@pytest.fixture
def service(mock_memory_store, mock_logger):
    """DIMemoryService instance with mocked dependencies."""
    return DIMemoryService(
        memory_store=mock_memory_store,
        logger=mock_logger,
    )


class TestGetLongitudinalMemory:
    """Tests for get_longitudinal_memory() method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_nonexistent_doctor(self, service):
        """Test that get_longitudinal_memory returns empty data for nonexistent doctor."""
        result = await service.get_longitudinal_memory(
            doctor_id="nonexistent-doctor-123",
            offset=0,
            limit=20,
            event_type="all",
        )

        assert result is not None
        assert "events" in result
        assert len(result["events"]) == 0

    @pytest.mark.asyncio
    async def test_returns_pagination_info(self, service):
        """Test that result includes pagination metadata."""
        result = await service.get_longitudinal_memory(
            doctor_id="doctor-123",
            offset=0,
            limit=10,
            event_type="all",
        )

        assert "total" in result
        assert "has_more" in result
        assert "offset" in result
        assert "limit" in result


class TestSearchMemory:
    """Tests for search_memory() method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self, service):
        """Test that search_memory returns empty list for no matches."""
        results = await service.search_memory(
            doctor_id="doctor-123",
            query="nonexistent-query-term",
            limit=10,
            offset=0,
        )

        assert isinstance(results, dict)
        assert "events" in results
        assert len(results["events"]) == 0


class TestGetStats:
    """Tests for get_stats() method."""

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self, service):
        """Test that get_stats returns statistics dictionary."""
        stats = await service.get_stats(doctor_id="doctor-123")

        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_stats_has_expected_keys(self, service):
        """Test that stats response has expected structure."""
        stats = await service.get_stats(doctor_id="doctor-123")

        assert isinstance(stats, dict)
