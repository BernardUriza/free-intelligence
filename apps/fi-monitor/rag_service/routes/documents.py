"""Document management endpoints (delete)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import state
from auth import verify_api_key

router = APIRouter()


@router.delete("/rag/documents/{filename}")
async def delete_document(
    filename: str,
    _auth: None = Depends(verify_api_key),
) -> dict:
    """Delete a specific document from the store.

    Phase 3: Cleanup endpoint to remove old documents from memory.
    Prevents confusion when switching between different PDFs.
    """
    if filename not in state._document_store:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")

    del state._document_store[filename]
    print(f"[RAG Service] Deleted document: {filename}")

    return {"status": "deleted", "filename": filename}


@router.delete("/rag/documents")
async def clear_all_documents(
    _auth: None = Depends(verify_api_key),
) -> dict:
    """Clear all documents from the store.

    Phase 3: Nuclear option - wipe entire document store.
    Useful for resetting state or clearing accumulated old docs.
    """
    count = len(state._document_store)
    state._document_store.clear()
    print(f"[RAG Service] Cleared {count} documents from store")

    return {"status": "cleared", "count": count}
