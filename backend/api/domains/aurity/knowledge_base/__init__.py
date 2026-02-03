"""Knowledge Base Domain - Document upload and RAG-powered search.

Endpoints:
- POST   /documents/upload - Upload document
- GET    /documents - List documents
- GET    /documents/{id} - Get document details
- PUT    /documents/{id} - Update document metadata
- DELETE /documents/{id} - Delete document
- POST   /documents/{id}/reindex - Re-process document
- POST   /documents/search - Semantic search

Features:
- Multi-tenancy: Documents filtered by clinic_id
- PDF/DOCX/TXT/MD text extraction
- Automatic chunking and embedding
- HDF5-based storage with vector index

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/api/routers/document/public/documents.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import documents

# Router with /documents prefix (added here, not in documents.py)
router = APIRouter(prefix="/documents", tags=["Documents"])
router.include_router(documents.router)

__all__ = ["router", "documents"]
