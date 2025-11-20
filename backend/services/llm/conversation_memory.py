"""
Conversation Memory Manager - Free Intelligence

Implementa "Memoria Longitudinal Unificada" (FI-PHIL-DOC-014)
"No existen sesiones. Solo una conversación infinita."

Arquitectura: Memory Index Centralizado (Pinecone-like en H5)
    storage/
    ├── sessions/{session-id}.h5       # Inmutable: audio + tasks
    └── memory_index/
        └── doctor-{id}/
            └── conversation_memory.h5  # Mutable: vector index
                ├── /embeddings/vectors (N, 384)
                ├── /metadata/session_ids [str]
                ├── /metadata/timestamps [int64]
                ├── /metadata/roles [str]
                ├── /metadata/content [str]
                └── /metadata/personas [str]

Basado en Cognitive Workspace (2025 research):
- Active memory management (no pasivo como RAG tradicional)
- Cross-session semantic search (54-60% memory reuse)
- Hierarchical context retrieval (recent + relevant + historical)
- Sub-linear growth O(log n) vs O(n)

Separación de concerns:
- Sessions H5: Immutable evidence packs (audio + tasks)
- Memory Index: Mutable vector store for semantic search
- Content refs: Apuntan a session H5 para full content

Author: Bernard Uriza Orozco
Created: 2025-11-18
Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from backend.compat import UTC, datetime
from pathlib import Path

import h5py
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.logger import get_logger

logger = get_logger(__name__)

# Memory index storage path
MEMORY_INDEX_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "memory_index"

# Embedding model (384-dim, local, no API keys needed)
_embedding_model: SentenceTransformer | None = None
_embedding_dim: int = 384  # all-MiniLM-L6-v2 dimensions
_memory_lock = threading.RLock()  # Lock for memory index writes


def get_embedding_model() -> SentenceTransformer:
    """Get singleton embedding model (lazy initialization).

    Model: all-MiniLM-L6-v2 (384 dimensions)
    - Fast: ~3000 sentences/sec on CPU
    - Lightweight: 80MB download
    - Local: No API keys, no cloud
    - Quality: 84.6% accuracy on STS benchmark

    Returns:
        SentenceTransformer model instance
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info("EMBEDDING_MODEL_INIT", model="all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


@dataclass
class Interaction:
    """Single conversation interaction (message + response).

    Attributes:
        session_id: Session identifier
        interaction_idx: Index in memory store
        timestamp: Unix timestamp
        role: "user" or "assistant"
        content: Text content
        embedding: 384-dim vector (for semantic search)
        persona: Persona used (optional)
        similarity: Similarity score (for search results)
    """

    session_id: str
    interaction_idx: int
    timestamp: int
    role: str
    content: str
    embedding: np.ndarray
    persona: str | None = None
    similarity: float = 0.0


@dataclass
class ConversationContext:
    """Retrieved conversation context for LLM prompt.

    Attributes:
        recent: Last N interactions (always included)
        relevant: Semantically relevant interactions from history
        summary: Consolidated summary of session (if exists)
        total_interactions: Total count across all sessions
    """

    recent: list[Interaction]
    relevant: list[Interaction]
    summary: str | None = None
    total_interactions: int = 0


class ConversationMemoryManager:
    """Manages conversation memory with centralized vector index.

    Implements "Pinecone-like" vector database in H5:
    - Single H5 file per doctor with all embeddings
    - Cross-session semantic search
    - Hierarchical retrieval (recent + relevant)
    - Append-only growth (aligned with FI philosophy)

    Storage structure:
        memory_index/doctor-{id}/conversation_memory.h5
        ├── /embeddings/vectors (N, 384) float32
        ├── /metadata/session_ids (N,) |S64
        ├── /metadata/timestamps (N,) int64
        ├── /metadata/roles (N,) |S16
        ├── /metadata/content (N,) |S4096
        └── /metadata/personas (N,) |S64

    Usage:
        >>> memory = ConversationMemoryManager(doctor_id="doc-123")
        >>> # Store interaction
        >>> memory.store_interaction(
        ...     session_id="session-456",
        ...     role="user",
        ...     content="What is the patient's diagnosis?",
        ...     persona="clinical_advisor"
        ... )
        >>> # Retrieve context
        >>> context = memory.get_context(
        ...     current_message="Can you explain the treatment options?",
        ...     session_id="session-456"
        ... )
        >>> # Build enriched prompt
        >>> prompt = memory.build_prompt(context, system_prompt, current_message)
    """

    def __init__(
        self,
        doctor_id: str,
        recent_buffer_size: int = 5,
        retrieval_top_k: int = 3,
    ):
        """Initialize conversation memory manager.

        Args:
            doctor_id: Doctor identifier (for memory isolation)
            recent_buffer_size: Number of recent interactions to always include
            retrieval_top_k: Number of relevant interactions to retrieve semantically
        """
        self.doctor_id = doctor_id
        self.recent_buffer_size = recent_buffer_size
        self.retrieval_top_k = retrieval_top_k
        self.embedding_model = get_embedding_model()

        # Memory index path
        self.memory_path = MEMORY_INDEX_PATH / doctor_id / "conversation_memory.h5"
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize H5 if doesn't exist
        self._initialize_memory_index()

    def _initialize_memory_index(self) -> None:
        """Initialize H5 memory index if doesn't exist.

        Creates:
        - /embeddings/vectors: (0, _embedding_dim) extensible float32 array
        - /metadata/*: Parallel arrays for session_ids, timestamps, roles, content, personas
        """
        if self.memory_path.exists():
            return  # Already initialized

        with _memory_lock, h5py.File(self.memory_path, "w") as f:
            # Embeddings: (N, _embedding_dim) float32, chunked for append performance
            f.create_dataset(
                "/embeddings/vectors",
                shape=(0, _embedding_dim),
                maxshape=(None, _embedding_dim),
                dtype=np.float32,
                chunks=(1000, _embedding_dim),  # 1000 interactions per chunk
                compression="lzf",  # Fast compression
            )

            # Metadata: parallel arrays (N,)
            metadata_group = f.create_group("/metadata")

            metadata_group.create_dataset(
                "session_ids",
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(encoding="utf-8", length=64),
                chunks=(1000,),
            )

            metadata_group.create_dataset(
                "timestamps",
                shape=(0,),
                maxshape=(None,),
                dtype=np.int64,
                chunks=(1000,),
            )

            metadata_group.create_dataset(
                "roles",
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(encoding="utf-8", length=16),
                chunks=(1000,),
            )

            metadata_group.create_dataset(
                "content",
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(encoding="utf-8", length=4096),
                chunks=(1000,),
            )

            metadata_group.create_dataset(
                "personas",
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(encoding="utf-8", length=64),
                chunks=(1000,),
            )

            # Store creation timestamp
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.attrs["doctor_id"] = self.doctor_id

        logger.info(
            "MEMORY_INDEX_INITIALIZED",
            doctor_id=self.doctor_id,
            path=str(self.memory_path),
        )

    def store_interaction(
        self,
        session_id: str,
        role: str,
        content: str,
        persona: str | None = None,
    ) -> int:
        """Store interaction in memory index with embedding.

        Appends to centralized H5 index for cross-session search.

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Text content
            persona: Persona used (optional)

        Returns:
            Index of stored interaction
        """
        start_time = time.time()

        # Generate embedding
        embedding = self.embedding_model.encode(content, convert_to_numpy=True)
        timestamp = int(datetime.now(UTC).timestamp())

        # Append to H5 index
        with _memory_lock, h5py.File(self.memory_path, "a") as f:
            # Get current size
            current_size = f["/embeddings/vectors"].shape[0]
            new_size = current_size + 1

            # Resize all datasets
            f["/embeddings/vectors"].resize((new_size, _embedding_dim))
            f["/metadata/session_ids"].resize((new_size,))
            f["/metadata/timestamps"].resize((new_size,))
            f["/metadata/roles"].resize((new_size,))
            f["/metadata/content"].resize((new_size,))
            f["/metadata/personas"].resize((new_size,))

            # Append data
            f["/embeddings/vectors"][current_size] = embedding
            f["/metadata/session_ids"][current_size] = session_id
            f["/metadata/timestamps"][current_size] = timestamp
            f["/metadata/roles"][current_size] = role
            f["/metadata/content"][current_size] = content[:4096]  # Truncate if needed
            f["/metadata/personas"][current_size] = persona or ""

            # Flush to disk
            f.flush()

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "CONVERSATION_MEMORY_STORED",
            doctor_id=self.doctor_id,
            session_id=session_id,
            role=role,
            content_length=len(content),
            embedding_dim=len(embedding),
            interaction_idx=current_size,
            latency_ms=latency_ms,
        )

        return current_size

    def get_context(
        self,
        current_message: str,
        session_id: str | None = None,
    ) -> ConversationContext:
        """Retrieve conversation context for LLM prompt.

        Implements hierarchical retrieval:
        1. Recent context: Last N interactions (from current session if specified)
        2. Relevant context: Top-K semantically similar interactions (cross-session)

        Args:
            current_message: Current user message (for semantic search)
            session_id: Optional session filter for recent context

        Returns:
            ConversationContext with recent + relevant interactions
        """
        start_time = time.time()

        # Generate embedding for current message
        query_embedding = self.embedding_model.encode(current_message, convert_to_numpy=True)

        recent: list[Interaction] = []
        relevant: list[Interaction] = []
        total_interactions = 0

        with h5py.File(self.memory_path, "r") as f:
            total_interactions = f["/embeddings/vectors"].shape[0]

            if total_interactions == 0:
                # Empty memory index
                return ConversationContext(
                    recent=[],
                    relevant=[],
                    total_interactions=0,
                )

            # Load all data (vectorized operations)
            embeddings = f["/embeddings/vectors"][:]  # (N, _embedding_dim)
            # Decode bytes as UTF-8 explicitly (h5py stores as bytes)
            session_ids = [
                s.decode("utf-8") if isinstance(s, bytes) else str(s)
                for s in f["/metadata/session_ids"][:]  # type: ignore[union-attr]
            ]
            timestamps = f["/metadata/timestamps"][:]
            roles = [
                r.decode("utf-8") if isinstance(r, bytes) else str(r)
                for r in f["/metadata/roles"][:]  # type: ignore[union-attr]
            ]
            content = [
                c.decode("utf-8") if isinstance(c, bytes) else str(c)
                for c in f["/metadata/content"][:]  # type: ignore[union-attr]
            ]
            personas = [
                p.decode("utf-8") if isinstance(p, bytes) else str(p)
                for p in f["/metadata/personas"][:]  # type: ignore[union-attr]
            ]

        # 1. Get recent context (last N from current session)
        if session_id:
            # Filter by session (ensure arrays are at least 1D)
            session_ids_array = np.atleast_1d(session_ids)
            session_mask = session_ids_array == session_id
            session_indices = np.where(session_mask)[0]

            if len(session_indices) > 0:
                # Get last N from this session
                recent_indices = session_indices[-self.recent_buffer_size :]
                recent = [
                    Interaction(
                        session_id=session_ids_array[idx],
                        interaction_idx=int(idx),
                        timestamp=int(timestamps[idx]),
                        role=roles[idx],
                        content=content[idx],
                        embedding=embeddings[idx],
                        persona=personas[idx] if personas[idx] else None,
                    )
                    for idx in recent_indices
                ]
        else:
            # Get last N globally
            recent_indices = np.arange(
                max(0, total_interactions - self.recent_buffer_size),
                total_interactions,
            )
            recent = [
                Interaction(
                    session_id=session_ids[idx],
                    interaction_idx=int(idx),
                    timestamp=int(timestamps[idx]),
                    role=roles[idx],
                    content=content[idx],
                    embedding=embeddings[idx],
                    persona=personas[idx] if personas[idx] else None,
                )
                for idx in recent_indices
            ]

        # 2. Get relevant context (semantic search, excluding recent)
        recent_indices_set = set(int(i.interaction_idx) for i in recent)

        # Compute cosine similarity (vectorized)
        # scores = embeddings @ query / (||embeddings|| * ||query||)
        norms = np.linalg.norm(embeddings, axis=1)  # type: ignore[call-overload]
        query_norm = np.linalg.norm(query_embedding)
        similarities = embeddings @ query_embedding / (norms * query_norm)

        # Exclude recent interactions
        available_mask = np.ones(total_interactions, dtype=bool)
        for idx in recent_indices_set:
            available_mask[idx] = False

        available_similarities = similarities.copy()
        available_similarities[~available_mask] = -1  # Mark excluded

        # Get top-K
        top_k_indices = np.argsort(available_similarities)[-self.retrieval_top_k :][::-1]
        top_k_indices = top_k_indices[available_similarities[top_k_indices] > 0]  # Filter valid

        relevant = [
            Interaction(
                session_id=session_ids[idx],
                interaction_idx=int(idx),
                timestamp=int(timestamps[idx]),
                role=roles[idx],
                content=content[idx],
                embedding=embeddings[idx],
                persona=personas[idx] if personas[idx] else None,
                similarity=float(similarities[idx]),
            )
            for idx in top_k_indices
        ]

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "CONVERSATION_MEMORY_RETRIEVED",
            doctor_id=self.doctor_id,
            session_id=session_id,
            recent_count=len(recent),
            relevant_count=len(relevant),
            total_interactions=total_interactions,
            latency_ms=latency_ms,
        )

        return ConversationContext(
            recent=recent,
            relevant=relevant,
            total_interactions=total_interactions,
        )

    def build_prompt(
        self,
        context: ConversationContext,
        system_prompt: str,
        current_message: str,
    ) -> str:
        """Build enriched prompt with conversation context.

        Format:
            {system_prompt}

            Relevant context from previous conversations:
            {relevant interactions with similarity scores}

            Recent conversation:
            {recent interactions}

            User: {current_message}

            Assistant:

        Args:
            context: Retrieved conversation context
            system_prompt: Base system prompt from persona
            current_message: Current user message

        Returns:
            Enriched prompt with full context
        """
        prompt_parts = [system_prompt]

        # Add relevant historical context (with similarity scores)
        if context.relevant:
            prompt_parts.append("\nRelevant context from previous conversations:")
            for interaction in context.relevant:
                similarity_pct = int(interaction.similarity * 100)
                prompt_parts.append(
                    f"[{similarity_pct}% relevant] {interaction.role.capitalize()}: {interaction.content}"
                )
            prompt_parts.append("")  # Empty line

        # Add recent conversation
        if context.recent:
            prompt_parts.append("Recent conversation:")
            for interaction in context.recent:
                prompt_parts.append(f"{interaction.role.capitalize()}: {interaction.content}")
            prompt_parts.append("")  # Empty line

        # Add current message
        prompt_parts.append(f"User: {current_message}\n\nAssistant:")

        return "\n".join(prompt_parts)

    def get_stats(self) -> dict:
        """Get memory index statistics.

        Returns:
            Dict with total_interactions, unique_sessions, oldest_timestamp, etc.
        """
        if not self.memory_path.exists():
            return {
                "total_interactions": 0,
                "unique_sessions": 0,
                "memory_index_exists": False,
            }

        with h5py.File(self.memory_path, "r") as f:
            total = f["/embeddings/vectors"].shape[0]
            if total == 0:
                return {
                    "total_interactions": 0,
                    "unique_sessions": 0,
                    "memory_index_exists": True,
                }

            session_ids = f["/metadata/session_ids"][:].astype(str)
            timestamps = f["/metadata/timestamps"][:]

            unique_sessions = len(set(session_ids))
            oldest_ts = int(timestamps.min())
            newest_ts = int(timestamps.max())

            return {
                "total_interactions": int(total),
                "unique_sessions": unique_sessions,
                "oldest_timestamp": oldest_ts,
                "newest_timestamp": newest_ts,
                "memory_index_exists": True,
                "doctor_id": self.doctor_id,
            }

    def get_paginated_history(
        self,
        offset: int = 0,
        limit: int = 50,
        session_id: str | None = None,
    ) -> dict:
        """Get paginated conversation history (chronological order).

        For infinite scroll implementation in UI.

        Args:
            offset: Number of interactions to skip (from newest)
            limit: Max interactions to return
            session_id: Optional session filter

        Returns:
            Dict with:
            - interactions: List of Interaction objects
            - total: Total count
            - has_more: Boolean indicating if more messages exist

        Example:
            >>> # Get latest 50 messages
            >>> page1 = memory.get_paginated_history(offset=0, limit=50)
            >>> # Get next 50 (older messages)
            >>> page2 = memory.get_paginated_history(offset=50, limit=50)
        """
        if not self.memory_path.exists():
            return {
                "interactions": [],
                "total": 0,
                "has_more": False,
            }

        with h5py.File(self.memory_path, "r") as f:
            total = f["/embeddings/vectors"].shape[0]

            if total == 0:
                return {
                    "interactions": [],
                    "total": 0,
                    "has_more": False,
                }

            # Load all metadata (decoded)
            session_ids = [
                s.decode("utf-8") if isinstance(s, bytes) else str(s)
                for s in f["/metadata/session_ids"][:]  # type: ignore[union-attr]
            ]
            timestamps = f["/metadata/timestamps"][:]
            roles = [
                r.decode("utf-8") if isinstance(r, bytes) else str(r)
                for r in f["/metadata/roles"][:]  # type: ignore[union-attr]
            ]
            content = [
                c.decode("utf-8") if isinstance(c, bytes) else str(c)
                for c in f["/metadata/content"][:]  # type: ignore[union-attr]
            ]
            personas = [
                p.decode("utf-8") if isinstance(p, bytes) else str(p)
                for p in f["/metadata/personas"][:]  # type: ignore[union-attr]
            ]
            embeddings = f["/embeddings/vectors"][:]

            # Filter by session if specified
            if session_id:
                session_mask = np.array(session_ids) == session_id
                indices = np.where(session_mask)[0]
            else:
                indices = np.arange(total)

            # Sort by timestamp (newest first for pagination)
            sorted_indices = indices[np.argsort(timestamps[indices])[::-1]]

            # Apply offset and limit
            paginated_indices = sorted_indices[offset : offset + limit]

            # Build interaction objects
            interactions = [
                Interaction(
                    session_id=session_ids[idx],
                    interaction_idx=int(idx),
                    timestamp=int(timestamps[idx]),
                    role=roles[idx],
                    content=content[idx],
                    embedding=embeddings[idx],
                    persona=personas[idx] if personas[idx] else None,
                )
                for idx in paginated_indices
            ]

            has_more = (offset + limit) < len(sorted_indices)

            return {
                "interactions": interactions,
                "total": len(sorted_indices),
                "has_more": has_more,
            }


# ============================================================================
# Singleton instances per doctor
# ============================================================================

_memory_managers: dict[str, ConversationMemoryManager] = {}
_manager_lock = threading.Lock()


def get_memory_manager(doctor_id: str) -> ConversationMemoryManager:
    """Get singleton memory manager for doctor.

    Args:
        doctor_id: Doctor identifier

    Returns:
        ConversationMemoryManager instance for doctor
    """
    global _memory_managers

    if doctor_id not in _memory_managers:
        with _manager_lock:
            # Double-check inside lock
            if doctor_id not in _memory_managers:
                _memory_managers[doctor_id] = ConversationMemoryManager(doctor_id)

    return _memory_managers[doctor_id]
