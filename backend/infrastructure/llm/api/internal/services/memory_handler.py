"""Chat Memory Handler Service.

Single Responsibility: Store and broadcast conversation interactions.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor from chat.py monolith)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.api.domains.aurity.assistant.websocket import broadcast_new_message
from backend.services.llm.services.conversation_memory import get_memory_manager
from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.services.llm.services.conversation_memory import MemoryManager

logger = get_logger(__name__)


class ChatMemoryHandler:
    """Handles conversation memory storage and WebSocket broadcasting.

    Single Responsibility: Only handles memory persistence and real-time updates.
    """

    def get_memory(self, doctor_id: str) -> "MemoryManager | None":
        """Get memory manager for a doctor.

        Args:
            doctor_id: Doctor identifier

        Returns:
            MemoryManager instance or None if not available
        """
        return get_memory_manager(doctor_id)

    async def store_user_message(
        self,
        memory: "MemoryManager",
        doctor_id: str,
        session_id: str | None,
        message: str,
        persona: str,
        broadcast: bool = True,
    ) -> None:
        """Store user message in memory and optionally broadcast.

        Args:
            memory: Memory manager instance
            doctor_id: Doctor identifier
            session_id: Session identifier
            message: User's message content
            persona: Persona identifier
            broadcast: Whether to broadcast via WebSocket
        """
        memory.store_interaction(
            session_id=session_id or "unknown",
            role="user",
            content=message,
            persona=persona,
        )

        if broadcast:
            timestamp = datetime.now(UTC).isoformat()
            await broadcast_new_message(
                doctor_id=doctor_id,
                role="user",
                content=message,
                timestamp=timestamp,
                persona=persona,
            )

        logger.debug(
            "USER_MESSAGE_STORED",
            doctor_id=doctor_id,
            session_id=session_id,
            message_length=len(message),
        )

    async def store_assistant_message(
        self,
        memory: "MemoryManager",
        doctor_id: str,
        session_id: str | None,
        content: str,
        persona: str,
        model: str,
        broadcast: bool = True,
    ) -> None:
        """Store assistant response in memory and optionally broadcast.

        Args:
            memory: Memory manager instance
            doctor_id: Doctor identifier
            session_id: Session identifier
            content: Assistant's response content
            persona: Persona identifier
            model: LLM model name
            broadcast: Whether to broadcast via WebSocket
        """
        memory.store_interaction(
            session_id=session_id or "unknown",
            role="assistant",
            content=content,
            persona=persona,
            model=model,
        )

        if broadcast:
            timestamp = datetime.now(UTC).isoformat()
            await broadcast_new_message(
                doctor_id=doctor_id,
                role="assistant",
                content=content,
                timestamp=timestamp,
                persona=persona,
                model=model,
            )

        logger.debug(
            "ASSISTANT_MESSAGE_STORED",
            doctor_id=doctor_id,
            session_id=session_id,
            content_length=len(content),
            model=model,
        )
