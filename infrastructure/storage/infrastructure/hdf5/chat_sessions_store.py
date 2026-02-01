"""Ephemeral storage for chat voice sessions.

Philosophy:
  Chat voice input is EPHEMERAL (not persistent like medical consultations).
  - One active session per user (user_id scoped)
  - Automatic cleanup on new session start
  - No audio persistence (only transcripts)
  - No post-processing (diarization/SOAP/encryption)

Architecture:
  - In-memory dict (thread-safe with RLock)
  - Session ID = "chat_{user_id}" (e.g., "chat_google-oauth2|123456")
  - Cleared on each new recording from same user

Storage structure:
  {
    "chat_user_123": ChatSession(
      session_id="chat_user_123",
      chunks=[
        ChatChunk(chunk_number=0, transcript="hola", timestamp=1234567890, ...),
        ChatChunk(chunk_number=1, transcript="cómo estás", timestamp=1234567893, ...),
      ],
      status="in_progress",
      created_at="2025-11-20T14:30:22Z"
    )
  }

Lifecycle:
  1. User starts recording → clear_chat_session() → reset chunks
  2. Each 3s chunk → add_chat_chunk() → append to list
  3. User stops recording → get_chat_transcript() → concatenate all chunks
  4. User sends message → chat message sent
  5. User starts new recording → clear_chat_session() → OVERWRITE previous

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: Voice chat integration (ephemeral storage)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# In-memory storage (thread-safe)
# Key = session_id (e.g., "chat_google-oauth2|123456")
# Value = ChatSession
_chat_sessions: dict[str, ChatSession] = {}
_chat_lock = threading.RLock()  # RLock allows same thread to acquire multiple times


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ChatChunk:
    """Single audio chunk transcription (3s segment)."""

    chunk_number: int
    transcript: str
    timestamp: float  # Unix timestamp
    provider: str  # deepgram, azure_whisper
    confidence: float = 0.0


@dataclass
class ChatSession:
    """Ephemeral chat voice session.

    Note: Audio bytes are NOT stored (ephemeral).
    Only transcripts are kept in memory for current session.
    """

    session_id: str
    chunks: list[ChatChunk] = field(default_factory=list)
    status: str = "in_progress"  # in_progress | completed
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PUBLIC API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def clear_chat_session(session_id: str) -> None:
    """Clear existing chat session (called when user starts new recording).

    Thread-safe operation.

    Args:
        session_id: Chat session ID (e.g., "chat_google-oauth2|123456")

    Example:
        clear_chat_session("chat_user_123")  # Resets chunk list
    """
    with _chat_lock:
        if session_id in _chat_sessions:
            old_chunks = len(_chat_sessions[session_id].chunks)
            del _chat_sessions[session_id]
            logger.info(
                "CHAT_SESSION_CLEARED",
                session_id=session_id,
                old_chunks=old_chunks,
            )
        else:
            logger.info("CHAT_SESSION_NOT_FOUND", session_id=session_id, action="clear")


def add_chat_chunk(
    session_id: str,
    chunk_number: int,
    transcript: str,
    provider: str,
    confidence: float = 0.0,
) -> None:
    """Add transcription chunk to chat session.

    Thread-safe operation.
    Creates session if not exists.

    Args:
        session_id: Chat session ID
        chunk_number: Chunk index (0, 1, 2, ...)
        transcript: Transcription text
        provider: STT provider (deepgram, azure_whisper)
        confidence: Transcription confidence (0.0-1.0)

    Example:
        add_chat_chunk("chat_user_123", 0, "hola mundo", "deepgram", 0.95)
    """
    with _chat_lock:
        # Create session if not exists
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = ChatSession(session_id=session_id)
            logger.info("CHAT_SESSION_CREATED", session_id=session_id)

        chunk = ChatChunk(
            chunk_number=chunk_number,
            transcript=transcript,
            timestamp=datetime.now(UTC).timestamp(),
            provider=provider,
            confidence=confidence,
        )

        _chat_sessions[session_id].chunks.append(chunk)

        logger.info(
            "CHAT_CHUNK_ADDED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=provider,
            transcript_preview=transcript[:50] if len(transcript) > 50 else transcript,
        )


def get_chat_session(session_id: str) -> ChatSession | None:
    """Get chat session (for polling/monitor).

    Thread-safe operation.

    Args:
        session_id: Chat session ID

    Returns:
        ChatSession if exists, None otherwise

    Example:
        session = get_chat_session("chat_user_123")
        if session:
            print(f"Found {len(session.chunks)} chunks")
    """
    with _chat_lock:
        session = _chat_sessions.get(session_id)
        # DEBUG: Log all sessions in memory
        logger.debug(
            "GET_CHAT_SESSION",
            session_id=session_id,
            found=session is not None,
            total_sessions_in_memory=len(_chat_sessions),
            all_session_ids=list(_chat_sessions.keys()),
        )
        return session


def get_chat_transcript(session_id: str) -> str:
    """Get full transcript from all chunks (concatenated).

    Thread-safe operation.

    Args:
        session_id: Chat session ID

    Returns:
        Concatenated transcript string (space-separated)

    Example:
        text = get_chat_transcript("chat_user_123")
        # Returns: "hola cómo estás bien gracias"
    """
    session = get_chat_session(session_id)
    if not session:
        return ""

    # Sort chunks by number and join with spaces
    sorted_chunks = sorted(session.chunks, key=lambda c: c.chunk_number)
    return " ".join(c.transcript for c in sorted_chunks)


def mark_chat_session_completed(session_id: str) -> None:
    """Mark chat session as completed.

    Thread-safe operation.

    Args:
        session_id: Chat session ID

    Example:
        mark_chat_session_completed("chat_user_123")
    """
    with _chat_lock:
        if session_id in _chat_sessions:
            _chat_sessions[session_id].status = "completed"
            logger.info("CHAT_SESSION_COMPLETED", session_id=session_id)


def get_all_chat_sessions() -> dict[str, ChatSession]:
    """Get all active chat sessions (for debugging/monitoring).

    Thread-safe operation.

    Returns:
        Dict of session_id -> ChatSession

    Example:
        sessions = get_all_chat_sessions()
        print(f"Active chat sessions: {len(sessions)}")
    """
    with _chat_lock:
        return _chat_sessions.copy()
