"""Chunk Handler Factory - Strategy Pattern selector.

Philosophy:
  Factory pattern to select the appropriate ChunkHandler implementation
  based on workflow mode.

  Design decision: Use mode parameter instead of session_id prefix detection.
  Rationale: Explicit is better than implicit (PEP 20).

Architecture:
  mode="medical" → MedicalChunkHandler (HDF5 persistent)

Note:
  mode="chat" was removed - the previous implementation was broken (syntax errors,
  missing functions). If chat mode is needed, implement ChatChunkHandler properly.

Usage:
  from backend.infrastructure.common.services.chunk_handler_factory import get_chunk_handler

  handler = get_chunk_handler(mode="medical")
  await handler.initialize_session(session_id)

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: Voice chat integration (factory)
"""

from __future__ import annotations

from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.infrastructure.common.services.chunk_handler import ChunkHandler
from backend.infrastructure.common.services.medical_chunk_handler import MedicalChunkHandler
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


def get_chunk_handler(mode: str) -> ChunkHandler:
    """Get chunk handler based on workflow mode.

    Factory function implementing Strategy Pattern.
    Currently only supports "medical" mode.

    Args:
        mode: Workflow mode - "medical" (only supported mode)

    Returns:
        ChunkHandler instance (MedicalChunkHandler)

    Raises:
        ValueError: If mode is invalid
        NotImplementedError: If mode is "chat" (not implemented)

    Example:
        handler = get_chunk_handler("medical")
        await handler.initialize_session("session_uuid", {"patient_name": "Juan"})
    """
    if mode == "medical":
        logger.debug("CHUNK_HANDLER_SELECTED", mode="medical", handler="MedicalChunkHandler")
        return MedicalChunkHandler(task_repository=get_task_repository())

    if mode == "chat":
        logger.error("CHAT_MODE_NOT_IMPLEMENTED", mode=mode)
        raise NotImplementedError(
            "Chat mode is not implemented. The previous implementation was broken. "
            "For voice chat transcription, use mode='medical' or implement ChatChunkHandler."
        )

    logger.error("INVALID_CHUNK_HANDLER_MODE", mode=mode, valid_modes=["medical"])
    raise ValueError(f"Invalid mode: '{mode}'. Expected 'medical'.")
