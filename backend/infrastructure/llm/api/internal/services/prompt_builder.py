"""Chat Prompt Builder Service.

Single Responsibility: Build prompts for LLM chat, with or without memory context.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor from chat.py monolith)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.services.llm.services.conversation_memory import (
        ConversationContext,
        MemoryManager,
    )
    from backend.services.llm.services.persona_manager import PersonaManager

    from ..schemas import ChatMessage

logger = get_logger(__name__)


@dataclass
class BuiltPrompt:
    """Result of prompt building."""

    prompt: str
    memory_context: ConversationContext | None = None
    memory_enabled: bool = False


class ChatPromptBuilder:
    """Builds prompts for LLM chat with optional conversation memory.

    Single Responsibility: Only handles prompt construction logic.
    """

    def __init__(self, persona_manager: "PersonaManager") -> None:
        self.persona_manager = persona_manager

    def build_with_memory(
        self,
        message: str,
        persona: str,
        context: dict[str, Any] | None,
        memory: "MemoryManager",
        session_id: str | None,
    ) -> BuiltPrompt:
        """Build prompt using conversation memory for context.

        Args:
            message: User's current message
            persona: Persona identifier
            context: Additional context dict
            memory: Memory manager instance
            session_id: Session identifier

        Returns:
            BuiltPrompt with memory-enriched prompt
        """
        memory_context = memory.get_context(
            current_message=message,
            session_id=session_id,
        )

        system_prompt = self.persona_manager.build_system_prompt(persona, context)
        prompt = memory.build_prompt(
            context=memory_context,
            system_prompt=system_prompt,
            current_message=message,
        )

        logger.debug(
            "PROMPT_BUILT_WITH_MEMORY",
            persona=persona,
            prompt_length=len(prompt),
            recent_count=len(memory_context.recent),
            relevant_count=len(memory_context.relevant),
        )

        return BuiltPrompt(
            prompt=prompt,
            memory_context=memory_context,
            memory_enabled=True,
        )

    def build_without_memory(
        self,
        message: str,
        persona: str,
        context: dict[str, Any] | None,
        messages: list["ChatMessage"] | None = None,
    ) -> BuiltPrompt:
        """Build prompt without conversation memory.

        Args:
            message: User's current message
            persona: Persona identifier
            context: Additional context dict
            messages: Optional conversation history (OpenAI format)

        Returns:
            BuiltPrompt without memory context
        """
        prompt = self.persona_manager.build_system_prompt(persona, context)

        if messages and len(messages) > 0:
            # Use client-provided conversation history
            conversation_parts = []
            for msg in messages:
                if msg.role == "system":
                    continue
                elif msg.role == "user":
                    conversation_parts.append(f"User: {msg.content}")
                elif msg.role == "assistant":
                    conversation_parts.append(f"Assistant: {msg.content}")

            if conversation_parts:
                prompt += "\n\n" + "\n\n".join(conversation_parts)
            prompt += "\n\nAssistant:"
        else:
            # Single message mode
            if context:
                prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"
            prompt += f"\n\nUser: {message}\n\nAssistant:"

        logger.debug(
            "PROMPT_BUILT_WITHOUT_MEMORY",
            persona=persona,
            prompt_length=len(prompt),
            has_message_history=bool(messages),
        )

        return BuiltPrompt(
            prompt=prompt,
            memory_context=None,
            memory_enabled=False,
        )
