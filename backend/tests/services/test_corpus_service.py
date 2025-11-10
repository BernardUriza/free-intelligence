"""Tests for CorpusService.

Validates corpus storage and retrieval functionality.
"""

from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.corpus_service import CorpusService


class TestCorpusService:
    """Test suite for CorpusService."""

    def test_create_corpus_service(self, corpus_service: CorpusService):
        """Test CorpusService instantiation."""
        assert corpus_service is not None

    def test_corpus_service_has_repository(self, corpus_service: CorpusService):
        """Test that corpus service has repository."""
        assert hasattr(corpus_service, "repository")

    def test_corpus_service_singleton(self, di_container):
        """Test that corpus service is singleton within container."""
        service1 = di_container.get_corpus_service()
        service2 = di_container.get_corpus_service()

        assert service1 is service2

    @pytest.mark.skip(reason="Requires HDF5 schema initialization")
    def test_store_interaction(self, corpus_service: CorpusService):
        """Test storing interaction in corpus (requires schema)."""
        # This test requires proper HDF5 schema initialization
        # Skip in basic test suite
        pass

    @pytest.mark.skip(reason="Requires HDF5 schema initialization")
    def test_retrieve_interaction(self, corpus_service: CorpusService):
        """Test retrieving interaction from corpus (requires schema)."""
        # This test requires proper HDF5 schema initialization
        # Skip in basic test suite
        pass

    @pytest.mark.skip(reason="Requires HDF5 schema initialization")
    def test_append_only_enforcement(self, corpus_service: CorpusService):
        """Test that corpus enforces append-only operations."""
        # This test validates mutation policy enforcement
        # Skip in basic test suite
        pass
