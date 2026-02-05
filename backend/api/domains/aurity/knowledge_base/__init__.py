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

SOLID Refactor: 2026-02-03
Structure:
- schemas.py      - Pydantic request/response models
- dependencies.py - FastAPI DI
- routes.py       - API endpoints
- services/       - FileValidator, TextExtractor
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.domains.aurity.knowledge_base.routes import router as routes_router

# Router with /documents prefix
router = APIRouter(prefix="/documents", tags=["Documents"])
router.include_router(routes_router)

__all__ = ["router"]
