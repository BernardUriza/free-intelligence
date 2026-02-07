"""Conversation memory interface.

Manages chat conversation history and context windows.
Decouples conversation logic from storage implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Any


class IConversationMemory(ABC):
    """Chat conversation history management.

    Responsibilities:
    - Store conversation messages (user, assistant, system)
    - Retrieve conversation windows (last N messages)
    - Manage context window limits (token budgets)
    - Support conversation branching (multiple threads)

    Clean Architecture Benefits:
    - Services don't know how conversations are stored
    - Easy to test with in-memory mock
    - Can migrate from in-memory to Redis/PostgreSQL without changing services
    """

    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add message to conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system)
            content: Message text
            metadata: Optional metadata (model, tokens, timestamp, etc.)

        Returns:
            Message ID

        Raises:
            ValueError: If role is invalid or content is empty
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def get_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
        before_message_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve conversation messages.

        Args:
            conversation_id: Conversation UUID
            limit: Maximum messages to return (None = all messages)
            before_message_id: Get messages before this message (for pagination)

        Returns:
            List of message dicts with keys:
                - message_id: str
                - role: str (user, assistant, system)
                - content: str
                - metadata: dict[str, Any]
                - created_at: str (ISO 8601)
            Sorted by created_at DESC (most recent first)

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_context_window(
        self,
        conversation_id: str,
        max_tokens: int,
        model: str,
    ) -> list[dict[str, str]]:
        """Get conversation window fitting within token budget.

        Args:
            conversation_id: Conversation UUID
            max_tokens: Maximum tokens for context window
            model: Model identifier (for token estimation)

        Returns:
            List of messages formatted for LLM [{"role": "user", "content": "..."}]
            Truncated to fit within max_tokens (keeps most recent messages)

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def clear_conversation(self, conversation_id: str) -> bool:
        """Delete all messages in conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            True if deletion successful, False if conversation doesn't exist

        Raises:
            IOError: If delete operation fails
        """
        pass

    @abstractmethod
    def get_conversation_summary(self, conversation_id: str) -> dict[str, Any]:
        """Get conversation metadata summary.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Dict with keys:
                - conversation_id: str
                - message_count: int
                - total_tokens: int (estimated)
                - created_at: str (ISO 8601)
                - updated_at: str (ISO 8601)
                - participants: list[str] (user IDs)

        Raises:
            ValueError: If conversation doesn't exist
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def estimate_tokens(self, conversation_id: str, model: str) -> int:
        """Estimate total tokens in conversation.

        Args:
            conversation_id: Conversation UUID
            model: Model identifier (for tokenizer)

        Returns:
            Estimated token count

        Raises:
            IOError: If read operation fails
        """
        pass
