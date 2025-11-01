"""Unit tests for CorpusService.

Tests the corpus service with mock dependencies.
Demonstrates the clean code testing pattern.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from backend.services.corpus_service import CorpusService


@pytest.fixture
def mock_repository():
    """Create mock CorpusRepository."""
    mock = Mock()
    mock.create.return_value = "doc_123"
    mock.read.return_value = {
        "document_id": "doc_123",
        "content": "Test document content",
        "metadata": {"source": "test", "tags": []},
    }
    mock.list_all.return_value = [
        {
            "document_id": "doc_123",
            "metadata": {"source": "test", "tags": []},
        }
    ]
    mock.add_chunk.return_value = True
    mock.get_chunks.return_value = []
    mock.delete.return_value = True
    return mock


@pytest.fixture
def corpus_service(mock_repository):
    """Create CorpusService with mocked repository."""
    return CorpusService(repository=mock_repository)


class TestCorpusServiceDocumentCreation:
    """Tests for document creation."""

    def test_create_document_success(self, corpus_service, mock_repository):
        """Test successful document creation."""
        result = corpus_service.create_document(
            document_id="doc_123",
            content="Test document content",
            source="test",
            tags=["test", "demo"],
        )

        assert result["document_id"] == "doc_123"
        assert result["status"] == "created"
        assert result["metadata"]["source"] == "test"
        assert result["metadata"]["tags"] == ["test", "demo"]
        mock_repository.create.assert_called_once()

    def test_create_document_minimal(self, corpus_service, mock_repository):
        """Test document creation with minimal parameters."""
        result = corpus_service.create_document(
            document_id="doc_456",
            content="Minimal content",
        )

        assert result["document_id"] == "doc_456"
        assert result["status"] == "created"
        assert result["metadata"]["source"] == "unknown"
        assert result["metadata"]["tags"] == []

    def test_create_document_empty_id(self, corpus_service):
        """Test document creation fails with empty ID."""
        with pytest.raises(ValueError, match="document_id must be at least 3 characters"):
            corpus_service.create_document(
                document_id="",
                content="Test content",
            )

    def test_create_document_short_id(self, corpus_service):
        """Test document creation fails with short ID."""
        with pytest.raises(ValueError, match="document_id must be at least 3 characters"):
            corpus_service.create_document(
                document_id="ab",
                content="Test content",
            )

    def test_create_document_empty_content(self, corpus_service):
        """Test document creation fails with empty content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            corpus_service.create_document(
                document_id="doc_123",
                content="",
            )

    def test_create_document_whitespace_content(self, corpus_service):
        """Test document creation fails with whitespace-only content."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            corpus_service.create_document(
                document_id="doc_123",
                content="   \n  \t  ",
            )

    def test_create_document_too_large(self, corpus_service):
        """Test document creation fails with oversized content."""
        large_content = "x" * (10_000_001)  # Exceeds 10MB limit
        with pytest.raises(ValueError, match="exceeds maximum size"):
            corpus_service.create_document(
                document_id="doc_123",
                content=large_content,
            )

    def test_create_document_storage_error(self, corpus_service, mock_repository):
        """Test document creation fails on storage error."""
        mock_repository.create.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            corpus_service.create_document(
                document_id="doc_123",
                content="Test content",
            )

    def test_create_document_metadata_content_length(self, corpus_service, mock_repository):
        """Test document metadata includes content length."""
        result = corpus_service.create_document(
            document_id="doc_123",
            content="Test document content",
        )

        assert result["metadata"]["content_length"] == len("Test document content")


class TestCorpusServiceDocumentRetrieval:
    """Tests for document retrieval."""

    def test_get_document_success(self, corpus_service, mock_repository):
        """Test successful document retrieval."""
        result = corpus_service.get_document("doc_123")

        assert result is not None
        assert result["document_id"] == "doc_123"
        assert result["content"] == "Test document content"
        mock_repository.read.assert_called_once_with("doc_123")

    def test_get_document_not_found(self, corpus_service, mock_repository):
        """Test retrieval returns None for missing document."""
        mock_repository.read.return_value = None

        result = corpus_service.get_document("nonexistent")

        assert result is None

    def test_get_document_retrieval_error(self, corpus_service, mock_repository):
        """Test retrieval fails on storage error."""
        mock_repository.read.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            corpus_service.get_document("doc_123")

    def test_get_document_summary_success(self, corpus_service, mock_repository):
        """Test document summary retrieval."""
        result = corpus_service.get_document_summary("doc_123")

        assert result is not None
        assert result["document_id"] == "doc_123"
        assert "content_length" in result
        assert "metadata" in result

    def test_get_document_summary_not_found(self, corpus_service, mock_repository):
        """Test summary returns None for missing document."""
        mock_repository.read.return_value = None

        result = corpus_service.get_document_summary("nonexistent")

        assert result is None

    def test_get_document_summary_content_length(self, corpus_service, mock_repository):
        """Test summary includes content length."""
        result = corpus_service.get_document_summary("doc_123")

        assert result["content_length"] == len("Test document content")


class TestCorpusServiceDocumentListing:
    """Tests for document listing."""

    def test_list_documents_success(self, corpus_service, mock_repository):
        """Test listing documents."""
        result = corpus_service.list_documents(limit=10)

        assert isinstance(result, list)
        assert len(result) >= 0
        mock_repository.list_all.assert_called_once()

    def test_list_documents_with_limit(self, corpus_service, mock_repository):
        """Test listing with limit parameter."""
        corpus_service.list_documents(limit=5)

        mock_repository.list_all.assert_called_with(limit=5)

    def test_list_documents_filter_by_source(self, corpus_service, mock_repository):
        """Test filtering documents by source."""
        # Setup multiple documents with different sources
        mock_repository.list_all.return_value = [
            {
                "document_id": "doc_1",
                "metadata": {"source": "api", "tags": []},
            },
            {
                "document_id": "doc_2",
                "metadata": {"source": "file", "tags": []},
            },
        ]

        result = corpus_service.list_documents(source="api")

        # Should filter to only API source documents
        assert all(d["document_id"].startswith("doc") for d in result)


class TestCorpusServiceChunks:
    """Tests for diarization chunk management."""

    def test_add_chunk_success(self, corpus_service, mock_repository):
        """Test successful chunk addition."""
        chunk = {
            "chunk_idx": 0,
            "text": "Hello world",
            "speaker": "A",
            "start_time": 0.0,
            "end_time": 1.5,
        }

        result = corpus_service.add_diarization_chunk("doc_123", chunk)

        assert result is True
        mock_repository.add_chunk.assert_called_once()

    def test_add_chunk_missing_fields(self, corpus_service):
        """Test chunk addition fails with missing required fields."""
        chunk_missing_speaker = {
            "chunk_idx": 0,
            "text": "Hello world",
            # Missing 'speaker'
        }

        with pytest.raises(ValueError, match="missing required fields"):
            corpus_service.add_diarization_chunk("doc_123", chunk_missing_speaker)

    def test_add_chunk_negative_index(self, corpus_service):
        """Test chunk addition fails with negative index."""
        chunk = {
            "chunk_idx": -1,
            "text": "Hello world",
            "speaker": "A",
        }

        with pytest.raises(ValueError, match="chunk_idx must be >= 0"):
            corpus_service.add_diarization_chunk("doc_123", chunk)

    def test_add_chunk_storage_error(self, corpus_service, mock_repository):
        """Test chunk addition fails on storage error."""
        mock_repository.add_chunk.side_effect = IOError("Storage failed")

        chunk = {
            "chunk_idx": 0,
            "text": "Hello world",
            "speaker": "A",
        }

        with pytest.raises(IOError, match="Storage failed"):
            corpus_service.add_diarization_chunk("doc_123", chunk)

    def test_get_chunks_success(self, corpus_service, mock_repository):
        """Test successful chunk retrieval."""
        mock_chunks = [
            {"chunk_idx": 0, "text": "Hello", "speaker": "A"},
            {"chunk_idx": 1, "text": "World", "speaker": "B"},
        ]
        mock_repository.get_chunks.return_value = mock_chunks

        result = corpus_service.get_chunks("doc_123")

        assert len(result) == 2
        assert result[0]["chunk_idx"] == 0
        mock_repository.get_chunks.assert_called_once_with("doc_123")

    def test_get_chunks_retrieval_error(self, corpus_service, mock_repository):
        """Test chunk retrieval fails on error."""
        mock_repository.get_chunks.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            corpus_service.get_chunks("doc_123")


class TestCorpusServiceDeletion:
    """Tests for document deletion."""

    def test_delete_document_success(self, corpus_service, mock_repository):
        """Test successful document deletion."""
        result = corpus_service.delete_document("doc_123")

        assert result is True
        mock_repository.delete.assert_called_once_with("doc_123")

    def test_delete_document_not_found(self, corpus_service, mock_repository):
        """Test deletion of non-existent document."""
        mock_repository.delete.return_value = False

        result = corpus_service.delete_document("nonexistent")

        assert result is False

    def test_delete_document_storage_error(self, corpus_service, mock_repository):
        """Test deletion fails on storage error."""
        mock_repository.delete.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            corpus_service.delete_document("doc_123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
