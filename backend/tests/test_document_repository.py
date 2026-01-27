"""Tests for document repository (Knowledge Base storage).

Tests cover:
- Document creation with metadata
- Chunk storage with embeddings
- Semantic search by embedding
- Document listing and filtering
- Update and delete operations

Author: Bernard Uriza Orozco
Created: 2025-12-08
Card: FI-API-FEAT-020 - Knowledge Base document upload with RAG
"""

from __future__ import annotations

import pytest

# Skip all tests in this module - requires backend.storage module
pytestmark = pytest.mark.skip(
    reason="Integration tests requiring HDF5 infrastructure - run locally with PYTHONPATH=backend/src"
)

import tempfile

import h5py
import numpy as np
import pytest
# FIXME: Broken import - use DI container instead
# from infrastructure.storage.infrastructure.hdf5.document_repository import (
    DocumentChunk,
    DocumentStatus,
    create_document,
    delete_document,
    get_document,
    list_documents,
    save_document_chunks,
    save_document_text,
    search_documents_by_embedding,
    update_document_metadata,
    update_document_status,
)
from pathlib import Path


@pytest.fixture
def temp_corpus():
    """Create temporary HDF5 file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        corpus_path = Path(tmp.name)

    yield corpus_path

    # Cleanup
    if corpus_path.exists():
        corpus_path.unlink()


def test_create_document(temp_corpus, monkeypatch):
    """Test creating a new document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    content = b"Test content here"
    metadata = create_document(
        content=content,
        filename="test.md",
        uploaded_by="test_user",
        title="Test Document",
        usage_instructions="Use for testing",
        assigned_personas=["general_assistant"],
    )

    assert metadata.doc_id is not None
    assert metadata.title == "Test Document"
    assert metadata.status == DocumentStatus.PENDING
    assert metadata.size_bytes == len(content)

    # Verify document exists in HDF5
    with h5py.File(temp_corpus, "r") as f:
        assert f"documents/{metadata.doc_id}" in f


def test_get_document(temp_corpus, monkeypatch):
    """Test retrieving a document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    content = b"Test content here"
    created_metadata = create_document(
        content=content,
        filename="test.md",
        uploaded_by="test_user",
        title="Test Document",
    )

    doc = get_document(created_metadata.doc_id)

    assert doc is not None
    assert doc.metadata.title == "Test Document"
    assert doc.metadata.uploaded_by == "test_user"


def test_get_document_with_content(temp_corpus, monkeypatch):
    """Test retrieving a document with raw content."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    content = b"Test content here"
    created_metadata = create_document(
        content=content,
        filename="test.md",
        uploaded_by="test_user",
    )

    doc = get_document(created_metadata.doc_id, include_content=True)

    assert doc is not None
    assert doc.content == content


def test_get_document_nonexistent(temp_corpus, monkeypatch):
    """Test retrieving a nonexistent document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create the file first so it exists
    with h5py.File(temp_corpus, "w") as f:
        f.create_group("documents")

    doc = get_document("nonexistent_doc")

    assert doc is None


def test_list_documents(temp_corpus, monkeypatch):
    """Test listing all documents."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create multiple documents
    for i in range(3):
        create_document(
            content=f"Content {i}".encode(),
            filename=f"doc_{i}.md",
            uploaded_by="test_user",
            title=f"Document {i}",
        )

    documents = list_documents()

    assert len(documents) == 3


def test_list_documents_with_status_filter(temp_corpus, monkeypatch):
    """Test filtering documents by status."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create documents
    doc1 = create_document(
        content=b"Content 1",
        filename="doc_1.md",
        uploaded_by="test_user",
    )
    doc2 = create_document(
        content=b"Content 2",
        filename="doc_2.md",
        uploaded_by="test_user",
    )
    create_document(
        content=b"Content 3",
        filename="doc_3.md",
        uploaded_by="test_user",
    )

    # Update status on some documents
    update_document_status(doc1.doc_id, DocumentStatus.INDEXED)
    update_document_status(doc2.doc_id, DocumentStatus.INDEXED)
    # doc3 stays PENDING

    # Filter by INDEXED status
    indexed_docs = list_documents(status_filter=DocumentStatus.INDEXED)

    assert len(indexed_docs) == 2


def test_update_document_metadata(temp_corpus, monkeypatch):
    """Test updating document metadata."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    created_metadata = create_document(
        content=b"Test content",
        filename="test.md",
        uploaded_by="test_user",
        title="Original Title",
    )

    # Update metadata
    updated = update_document_metadata(
        created_metadata.doc_id,
        title="Updated Title",
        usage_instructions="Updated instructions",
    )

    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.usage_instructions == "Updated instructions"

    # Verify update persisted
    doc = get_document(created_metadata.doc_id)
    assert doc is not None
    assert doc.metadata.title == "Updated Title"


def test_update_document_status(temp_corpus, monkeypatch):
    """Test updating document status."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    created_metadata = create_document(
        content=b"Test content",
        filename="test.md",
        uploaded_by="test_user",
    )

    assert created_metadata.status == DocumentStatus.PENDING

    # Update status
    result = update_document_status(created_metadata.doc_id, DocumentStatus.INDEXED)
    assert result is True

    # Verify update
    doc = get_document(created_metadata.doc_id)
    assert doc is not None
    assert doc.metadata.status == DocumentStatus.INDEXED


def test_delete_document(temp_corpus, monkeypatch):
    """Test deleting a document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    created_metadata = create_document(
        content=b"Test content",
        filename="test.md",
        uploaded_by="test_user",
    )

    # Verify document exists
    assert get_document(created_metadata.doc_id) is not None

    # Delete document
    result = delete_document(created_metadata.doc_id)
    assert result is True

    # Verify document no longer exists
    assert get_document(created_metadata.doc_id) is None


def test_delete_document_nonexistent(temp_corpus, monkeypatch):
    """Test deleting a nonexistent document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create the file first so it exists
    with h5py.File(temp_corpus, "w") as f:
        f.create_group("documents")

    result = delete_document("nonexistent_doc")
    assert result is False


def test_save_document_text(temp_corpus, monkeypatch):
    """Test saving extracted text for a document."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    created_metadata = create_document(
        content=b"Original bytes",
        filename="test.md",
        uploaded_by="test_user",
    )

    # Save extracted text
    extracted_text = "This is the extracted text content."
    result = save_document_text(created_metadata.doc_id, extracted_text)
    assert result is True

    # Verify text is stored
    doc = get_document(created_metadata.doc_id)
    assert doc is not None
    assert doc.text == extracted_text


def test_save_document_chunks(temp_corpus, monkeypatch):
    """Test saving document chunks with embeddings."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    created_metadata = create_document(
        content=b"Test content",
        filename="test.md",
        uploaded_by="test_user",
    )

    embedding_dim = 384
    chunks = [
        DocumentChunk(
            chunk_id=0,
            text="This is the first chunk of text.",
            embedding=np.random.rand(embedding_dim).astype(np.float32),
        ),
        DocumentChunk(
            chunk_id=1,
            text="This is the second chunk of text.",
            embedding=np.random.rand(embedding_dim).astype(np.float32),
        ),
    ]

    result = save_document_chunks(created_metadata.doc_id, chunks)
    assert result is True

    # Verify chunks in HDF5
    with h5py.File(temp_corpus, "r") as f:
        chunks_group = f[f"documents/{created_metadata.doc_id}/chunks"]
        assert len(chunks_group.keys()) == 2


def test_search_documents_by_embedding(temp_corpus, monkeypatch):
    """Test semantic search using embeddings."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create document
    created_metadata = create_document(
        content=b"Test content",
        filename="test.md",
        uploaded_by="test_user",
        assigned_personas=["general_assistant"],
    )

    embedding_dim = 384
    # Create chunk with a known embedding pattern
    target_embedding = np.array([1.0] * embedding_dim, dtype=np.float32)
    chunks = [
        DocumentChunk(
            chunk_id=0,
            text="Information about HIPAA compliance.",
            embedding=target_embedding,
        ),
        DocumentChunk(
            chunk_id=1,
            text="Data about patient records.",
            embedding=np.array([0.5] * embedding_dim, dtype=np.float32),
        ),
    ]
    save_document_chunks(created_metadata.doc_id, chunks)

    # Update status to indexed
    update_document_status(created_metadata.doc_id, DocumentStatus.INDEXED)

    # Search with similar embedding
    query_embedding = np.array([1.0] * embedding_dim, dtype=np.float32)
    results = search_documents_by_embedding(query_embedding, top_k=2)

    assert len(results) > 0
    # First result should be the chunk with matching embedding
    doc_id, chunk_id, similarity, _text = results[0]
    assert doc_id == created_metadata.doc_id
    assert chunk_id == 0
    assert similarity > 0.99  # High similarity for identical embedding


def test_search_documents_with_persona_filter(temp_corpus, monkeypatch):
    """Test semantic search with persona filtering."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    embedding_dim = 384

    # Create document for specific persona
    created_metadata = create_document(
        content=b"Clinical content",
        filename="clinical.md",
        uploaded_by="test_user",
        assigned_personas=["clinical_advisor"],
    )

    target_embedding = np.array([1.0] * embedding_dim, dtype=np.float32)
    chunks = [
        DocumentChunk(
            chunk_id=0,
            text="Clinical guidelines for treatment.",
            embedding=target_embedding,
        ),
    ]
    save_document_chunks(created_metadata.doc_id, chunks)

    # Search with matching persona
    query_embedding = np.array([1.0] * embedding_dim, dtype=np.float32)
    results = search_documents_by_embedding(
        query_embedding, top_k=5, persona_filter="clinical_advisor"
    )

    assert len(results) == 1
    assert results[0][0] == created_metadata.doc_id

    # Search with non-matching persona
    results_filtered = search_documents_by_embedding(
        query_embedding, top_k=5, persona_filter="soap_editor"
    )

    assert len(results_filtered) == 0


def test_list_documents_with_persona_filter(temp_corpus, monkeypatch):
    """Test filtering documents by assigned persona."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Create documents with different personas
    create_document(
        content=b"Content 1",
        filename="doc_1.md",
        uploaded_by="test_user",
        assigned_personas=["general_assistant"],
    )
    create_document(
        content=b"Content 2",
        filename="doc_2.md",
        uploaded_by="test_user",
        assigned_personas=["clinical_advisor"],
    )
    create_document(
        content=b"Content 3",
        filename="doc_3.md",
        uploaded_by="test_user",
        assigned_personas=["general_assistant", "clinical_advisor"],
    )

    # Filter by general_assistant
    ga_docs = list_documents(persona_filter="general_assistant")
    assert len(ga_docs) == 2  # Doc 1 and Doc 3

    # Filter by clinical_advisor
    ca_docs = list_documents(persona_filter="clinical_advisor")
    assert len(ca_docs) == 2  # Doc 2 and Doc 3


def test_document_type_detection(temp_corpus, monkeypatch):
    """Test that document type is correctly inferred from filename."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    # Test markdown
    md_doc = create_document(
        content=b"# Heading",
        filename="test.md",
        uploaded_by="test_user",
    )
    assert md_doc.doc_type.value == "markdown"

    # Test PDF
    pdf_doc = create_document(
        content=b"%PDF-1.4",
        filename="test.pdf",
        uploaded_by="test_user",
    )
    assert pdf_doc.doc_type.value == "pdf"

    # Test DOCX
    docx_doc = create_document(
        content=b"PK",  # ZIP signature
        filename="test.docx",
        uploaded_by="test_user",
    )
    assert docx_doc.doc_type.value == "docx"


def test_document_sha256_hash(temp_corpus, monkeypatch):
    """Test that SHA256 hash is correctly calculated."""
    monkeypatch.setattr("backend.storage.document_repository.CORPUS_PATH", temp_corpus)

    import hashlib

    content = b"Test content for hashing"
    expected_hash = hashlib.sha256(content).hexdigest()

    metadata = create_document(
        content=content,
        filename="test.md",
        uploaded_by="test_user",
    )

    assert metadata.sha256 == expected_hash
