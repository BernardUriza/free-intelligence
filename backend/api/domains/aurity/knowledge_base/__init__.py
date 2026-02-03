"""Knowledge Base Domain - Document upload and RAG-powered search.

Endpoints:
- GET  /documents - List all documents
- POST /documents/upload - Upload document
- GET  /documents/{id} - Get document details
- POST /documents/search - RAG-powered semantic search
- POST /documents/{id}/reindex - Reindex document

Migrated from: backend/api/routers/document/public/documents.py
"""

from __future__ import annotations
