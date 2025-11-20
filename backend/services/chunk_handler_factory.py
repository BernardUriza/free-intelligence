"""Chunk Handler Factory - Strategy Pattern selector.

Philosophy:
  Factory pattern to select the appropriate ChunkHandler implementation
  based on workflow mode (medical vs chat).

  Design decision: Use mode parameter instead of session_id prefix detection.
  Rationale: Explicit is better than implicit (PEP 20).

Architecture:
  mode="medical" → MedicalChunkHandler (HDF5 persistent)
  mode="chat"    → ChatChunkHandler (in-memory ephemeral)

Usage:
  from backend.services.chunk_handler_factory import get_chunk_handler

  handler = get_chunk_handler(mode="medical")
  await handler.initialize_session(session_id)

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: Voice chat integration (factory)
"""

from __future__ import annotations

from backend.logger import get_logger
from backend.services.chat_chunk_handler import ChatChunkHandler
from backend.services.chunk_handler import ChunkHandler
from backend.services.medical_chunk_handler import MedicalChunkHandler

logger = get_logger(__name__)


def get_chunk_handler(mode: str) -> ChunkHandler:
    """Get chunk handler based on workflow mode.

    Factory function implementing Strategy Pattern.
    Selects the appropriate handler implementation based on mode.

    Args:
        mode: Workflow mode - "medical" | "chat"

    Returns:
        ChunkHandler instance (MedicalChunkHandler or ChatChunkHandler)

    Raises:
        ValueError: If mode is invalid

    Example:
        # Medical workflow (persistent HDF5)
        handler = get_chunk_handler("medical")
        await handler.initialize_session("session_uuid", {"patient_name": "Juan"})

        # Chat workflow (ephemeral in-memory)
        handler = get_chunk_handler("chat")
        await handler.initialize_session("chat_user_123", None)
    """
    if mode == "medical":
        logger.debug("CHUNK_HANDLER_SELECTED", mode="medical", handler="MedicalChunkHandler")
        return MedicalChunkHandler()

    elif mode == "chat":
        logger.debug("CHUNK_HANDLER_SELECTED", mode="chat", handler="ChatChunkHandler")
        return ChatChunkHandler()

    else:
        logger.error("INVALID_CHUNK_HANDLER_MODE", mode=mode, valid_modes=["medical", "chat"])
        raise ValueError(
            f"Invalid mode: '{mode}'. Expected 'medical' or 'chat'."
        )
