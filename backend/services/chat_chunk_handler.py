"""Chat workflow handler - In-memory ephemeral storage.

Philosophy:
  Chat voice input is ephemeral (not persistent like medical consultations).
  - No audio persistence (transcripts only)
  - No post-processing (diarization/SOAP)
  - Automatic cleanup on new session
  - Immediate transcription (no workers)

Architecture:
  - Storage: In-memory dict (chat_sessions_store.py)
  - Lifecycle: Ephemeral (cleared on new recording)
  - Session ID: "chat_{user_id}" (user-scoped)

Workflow:
  1. User clicks mic → initialize_session() → clear_chat_session()
  2. Each 3s → save_chunk() → add_chat_chunk() (in-memory)
  3. User stops → get_chat_transcript() → return concatenated text
  4. User clicks mic again → initialize_session() → OVERWRITE previous

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: Voice chat integration (chat handler)
"""

from __future__ import annotations

from typing import Any

from backend.logger import get_logger
from backend.services.chunk_handler import ChunkHandler
from backend.storage.chat_sessions_store import (
    add_chat_chunk,
    clear_chat_session,
    get_chat_session,
    mark_chat_session_completed,
)

logger = get_logger(__name__)


class ChatChunkHandler(ChunkHandler):
    """Handler for chat voice input workflow.

    Storage: In-memory dict (thread-safe)
    Lifecycle: Ephemeral (cleared on new session)
    Post-processing: None

    Example:
        handler = ChatChunkHandler()
        await handler.initialize_session("chat_user_123")
        await handler.save_chunk("chat_user_123", 0, b"audio", "hola", {...})
        status = await handler.get_session_status("chat_user_123")
        # status = {"total_chunks": 1, "chunks": [{"transcript": "hola", ...}]}
    """

    async def initialize_session(
        self,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Clear previous chat session.

        Chat sessions are ephemeral - each new recording overwrites the previous one.

        Args:
            session_id: Chat session ID (e.g., "chat_google-oauth2|123456")
            metadata: Optional user metadata (unused for chat)

        Behavior:
            - Deletes previous session from in-memory dict
            - Logs cleared chunk count
        """
        clear_chat_session(session_id)
        logger.info(
            "CHAT_SESSION_INITIALIZED",
            session_id=session_id,
            mode="chat",
        )

    async def save_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
        transcript: str,
        metadata: dict[str, Any],
    ) -> None:
        """Save chunk to in-memory store.

        Note: audio_bytes are NOT stored (ephemeral).
        Only transcripts are kept in memory.

        Args:
            session_id: Chat session ID
            chunk_number: Chunk index (0, 1, 2, ...)
            audio_bytes: Raw audio data (DISCARDED - not stored)
            transcript: Transcription text from STT
            metadata: Provider, confidence, timestamp, etc.

        Behavior:
            - Adds transcript + metadata to in-memory dict
            - Discards audio_bytes (not persisted)
        """
        # Discard audio_bytes (ephemeral - no persistence)
        # Only store transcript + metadata
        add_chat_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            transcript=transcript,
            provider=metadata.get("provider", "unknown"),
            confidence=metadata.get("confidence", 0.0),
        )

        logger.info(
            "CHAT_CHUNK_SAVED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=metadata.get("provider"),
            audio_discarded=True,  # Audio not persisted
        )

    async def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Read session status from in-memory store.

        Args:
            session_id: Chat session ID

        Returns:
            dict with keys:
                - session_id: str
                - status: str (always "completed" for chat)
                - total_chunks: int
                - processed_chunks: int (always == total_chunks)
                - progress_percent: int (always 100)
                - chunks: list[dict] (chunk metadata)

        Behavior:
            - Reads from in-memory dict
            - All chunks are immediately "completed" (no workers)
            - Returns 404-like dict if session not found
        """
        session = get_chat_session(session_id)

        if not session:
            logger.warning("CHAT_SESSION_NOT_FOUND", session_id=session_id)
            return {
                "session_id": session_id,
                "status": "not_found",
                "total_chunks": 0,
                "processed_chunks": 0,
                "progress_percent": 0,
                "chunks": [],
            }

        # Build chunks list from in-memory session
        chunks_list = [
            {
                "chunk_number": c.chunk_number,
                "transcript": c.transcript,
                "status": "completed",  # Chat chunks are immediately completed
                "provider": c.provider,
                "confidence": c.confidence,
                "timestamp": c.timestamp,
            }
            for c in session.chunks
        ]

        return {
            "session_id": session_id,
            "status": session.status,
            "total_chunks": len(session.chunks),
            "processed_chunks": len(session.chunks),  # Always 100% (no workers)
            "progress_percent": 100,
            "chunks": chunks_list,
        }

    async def finalize_session(self, session_id: str) -> dict[str, Any]:
        """No-op for chat (ephemeral, no post-processing).

        Chat sessions don't require post-processing:
        - No diarization (single speaker assumed)
        - No SOAP notes (not medical)
        - No encryption (ephemeral)

        Args:
            session_id: Chat session ID

        Returns:
            dict with success status

        Behavior:
            - Marks session as "completed" in memory
            - Returns success (no workers triggered)
        """
        mark_chat_session_completed(session_id)

        logger.info(
            "CHAT_SESSION_FINALIZED",
            session_id=session_id,
            post_processing=False,  # No diarization/SOAP
        )

        return {
            "session_id": session_id,
            "status": "completed",
            "post_processing": False,
        }
