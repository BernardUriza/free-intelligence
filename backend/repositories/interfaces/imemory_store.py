"""Longitudinal memory repository interface.

Stores patient history, session context, and learned preferences.
Decouples memory service from HDF5/PostgreSQL implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IMemoryStore(ABC):
    """Longitudinal patient memory storage.

    Responsibilities:
    - Store patient memories (clinical, contextual, preferences)
    - Retrieve memories by patient, type, and recency
    - Update memory importance/relevance scores
    - Delete expired or irrelevant memories

    Memory Types:
    - clinical: Diagnoses, medications, allergies
    - contextual: Session summaries, conversation patterns
    - preference: Communication style, language preferences
    - temporal: Time-series events (vitals, symptoms)

    Clean Architecture Benefits:
    - Memory service doesn't know about storage backend
    - Easy to test with in-memory mock
    - Can migrate from HDF5 to PostgreSQL/Redis without changing services
    """

    @abstractmethod
    def store_memory(
        self,
        patient_id: str,
        memory_type: str,
        content: Dict[str, Any],
        importance: float = 0.5,
        tags: List[str] | None = None,
    ) -> str:
        """Store memory entry.

        Args:
            patient_id: Patient UUID
            memory_type: Memory category (clinical, contextual, preference, temporal)
            content: Memory payload (flexible schema)
            importance: Relevance score 0.0-1.0 (used for retrieval ranking)
            tags: Optional tags for filtering (e.g., ["allergy", "medication"])

        Returns:
            Memory ID (UUID)

        Raises:
            ValueError: If patient_id is empty or memory_type is invalid
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def retrieve_memories(
        self,
        patient_id: str,
        memory_type: str | None = None,
        tags: List[str] | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent memories for patient.

        Args:
            patient_id: Patient UUID
            memory_type: Optional filter by type (None = all types)
            tags: Optional filter by tags (AND logic - must have all tags)
            limit: Maximum memories to return
            min_importance: Minimum importance score threshold

        Returns:
            List of memory dicts with keys:
                - memory_id: str
                - patient_id: str
                - memory_type: str
                - content: Dict[str, Any]
                - importance: float
                - tags: List[str]
                - created_at: str (ISO 8601)
                - updated_at: str (ISO 8601)
            Sorted by importance DESC, then created_at DESC

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_memory(self, memory_id: str) -> Dict[str, Any] | None:
        """Retrieve specific memory by ID.

        Args:
            memory_id: Memory UUID

        Returns:
            Memory dict (see retrieve_memories for structure)
            None if memory doesn't exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update memory metadata (importance, tags, content).

        Args:
            memory_id: Memory UUID
            updates: Dict of fields to update (importance, tags, content, etc.)

        Returns:
            True if update successful, False if memory not found

        Raises:
            IOError: If update operation fails
        """
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory entry.

        Args:
            memory_id: Memory UUID

        Returns:
            True if deletion successful, False if memory not found

        Raises:
            IOError: If delete operation fails
        """
        pass

    @abstractmethod
    def get_memory_count(
        self,
        patient_id: str,
        memory_type: str | None = None,
    ) -> int:
        """Get total memory count for patient.

        Args:
            patient_id: Patient UUID
            memory_type: Optional filter by type

        Returns:
            Number of memories (0 if patient doesn't exist)

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def search_memories(
        self,
        patient_id: str,
        query: str,
        memory_type: str | None = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search memories by content (semantic or keyword search).

        Args:
            patient_id: Patient UUID
            query: Search query string
            memory_type: Optional filter by type
            limit: Maximum results to return

        Returns:
            List of memory dicts (see retrieve_memories for structure)
            Sorted by relevance score

        Raises:
            IOError: If search operation fails
        """
        pass
