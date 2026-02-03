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

Migrated from: backend/api/routers/document/public/documents.py
"""

from __future__ import annotations

# Re-export router from legacy location
# Router already has prefix="/documents" so no additional prefix needed
from backend.api.routers.document.public.documents import router

__all__ = ["router"]
