"""Knowledge Base API dependencies.

FastAPI dependency injection for document service.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from backend.infrastructure.common.repository_singletons import (
    get_document_repository_singleton,
)
from backend.services.document.services.document_service import DocumentService


def get_document_service() -> DocumentService:
    """Get document service instance with HDF5 repository singleton.

    Uses centralized singleton to share vector index across all requests.
    Performance: Avoids reloading HDF5 vector index per-request.
    """
    repository = get_document_repository_singleton()
    return DocumentService(repository=repository)
