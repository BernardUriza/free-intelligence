"""
Conversation Memory Manager - Free Intelligence

Implementa "Memoria Longitudinal Unificada" (FI-PHIL-DOC-014)
"No existen sesiones. Solo una conversacion infinita."

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

Cloud Architecture (PHI-Safe):
    Cloud Backend --> FI Monitor (via Cloudflare Tunnel) --> GPU Embeddings

    The cloud backend does NOT run embeddings locally.
    All embedding operations are delegated to FI Monitor running on clinic hardware.

Basado en Cognitive Workspace (2025 research):
- Active memory management (no pasivo como RAG tradicional)
- Cross-session semantic search (54-60% memory reuse)
- Hierarchical context retrieval (recent + relevant + historical)
- Sub-linear growth O(log n) vs O(n)

Separacion de concerns:
- Sessions H5: Immutable evidence packs (audio + tasks)
- Memory Index: Mutable vector store for semantic search
- Content refs: Apuntan a session H5 para full content

Author: Bernard Uriza Orozco
Created: 2025-11-18
Updated: 2026-02-07 (Cloud refactor - embeddings via FI Monitor API)
Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import h5py
import httpx
import numpy as np
from pathlib import Path

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# Memory index storage path
MEMORY_INDEX_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "memory_index"

# Embedding configuration
_embedding_dim: int = 384  # all-MiniLM-L6-v2 dimensions
_memory_lock = threading.RLock()  # Lock for memory index writes

# FI Monitor configuration (for remote embeddings)
FI_MONITOR_URL = os.getenv("FI_MONITOR_URL", "")
RAG_API_KEY = os.getenv("RAG_API_KEY", "")

# httpx client singleton
_http_client: httpx.AsyncClient | None = None
_http_client_lock = threading.Lock()


def _get_http_client() -> httpx.AsyncClient:
    """Get singleton async HTTP client for FI Monitor API calls."""
    global _http_client
    if _http_client is None:
        with _http_client_lock:
            if _http_client is None:
                _http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0),
                    headers={"X-API-Key": RAG_API_KEY},
                )
    return _http_client


async def get_embeddings_from_fi(texts: list[str]) -> np.ndarray:
    """Get embeddings from FI Monitor RAG service.

    FI Monitor runs on clinic hardware with GPU and handles all
    embedding operations locally (PHI never leaves clinic).

    Args:
        texts: List of texts to embed

    Returns:
        numpy array of shape (len(texts), 384)

    Raises:
        RuntimeError: If FI Monitor is not configured or unavailable
    """
    if not FI_MONITOR_URL:
        raise RuntimeError(
            "FI_MONITOR_URL not configured. "
            "Embeddings require FI Monitor running on clinic hardware."
        )

    client = _get_http_client()

    try:
        response = await client.post(
            f"{FI_MONITOR_URL}/rag/embed",
            json={"texts": texts},
        )
        response.raise_for_status()

        data = response.json()
        embeddings = np.array(data["embeddings"], dtype=np.float32)

        logger.info(
            "EMBEDDINGS_FETCHED_FROM_FI_MONITOR",
            num_texts=len(texts),
            device=data.get("device", "unknown"),
            embedding_dim=embeddings.shape[1] if len(embeddings.shape) > 1 else 0,
        )

        return embeddings

    except httpx.HTTPStatusError as e:
        logger.error(
            "FI_MONITOR_EMBED_HTTP_ERROR",
            status_code=e.response.status_code,
            detail=str(e),
        )
        raise RuntimeError(f"FI Monitor embedding failed: {e.response.status_code}") from e
    except httpx.RequestError as e:
        logger.error(
            "FI_MONITOR_EMBED_CONNECTION_ERROR",
            error=str(e),
            url=FI_MONITOR_URL,
        )
        raise RuntimeError(f"FI Monitor unavailable: {e}") from e


def is_embeddings_available() -> bool:
    """Check if embedding service is available.

    Returns:
        True if FI_MONITOR_URL is configured, False otherwise
    """
    return bool(FI_MONITOR_URL)


@dataclass(kw_only=True)
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
        model: LLM model that generated response (for assistant messages)
        similarity: Similarity score (for search results)
    """

    session_id: str
    interaction_idx: int
    timestamp: int
    role: str
    content: str
    embedding: np.ndarray
    persona: str | None = None
    model: str | None = None
    similarity: float = 0.0


@dataclass(kw_only=True)
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
        ├── /metadata/personas (N,) |S64
        └── /metadata/models (N,) |S64

    Cloud Architecture:
        Embeddings are computed by FI Monitor (clinic GPU) via HTTP API.
        This class handles storage and retrieval; FI Monitor handles ML.

    Usage:
        >>> memory = ConversationMemoryManager(doctor_id="doc-123")
        >>> # Store interaction (async - calls FI Monitor for embedding)
        >>> await memory.store_interaction(
        ...     session_id="session-456",
        ...     role="user",
        ...     content="What is the patient's diagnosis?",
        ...     persona="clinical_advisor"
        ... )
        >>> # Retrieve context (async - calls FI Monitor for query embedding)
        >>> context = await memory.get_context(
        ...     current_message="Can you explain the treatment options?",
        ...     session_id="session-456"
        ... )
        >>> # Build enriched prompt (sync - no ML)
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

            metadata_group.create_dataset(
                "models",
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

    async def store_interaction(
        self,
        session_id: str,
        role: str,
        content: str,
        persona: str | None = None,
        model: str | None = None,
    ) -> int:
        """Store interaction in memory index with embedding.

        Appends to centralized H5 index for cross-session search.
        Embedding is computed by FI Monitor (async HTTP call).

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Text content
            persona: Persona used (optional)
            model: LLM model that generated response (for assistant messages)

        Returns:
            Index of stored interaction

        Raises:
            RuntimeError: If FI Monitor is unavailable
        """
        start_time = time.time()

        # Get embedding from FI Monitor
        embeddings = await get_embeddings_from_fi([content])
        embedding = embeddings[0]

        timestamp = int(datetime.now(UTC).timestamp())

        # Append to H5 index
        with _memory_lock, h5py.File(self.memory_path, "a") as f:
            # Create models dataset if it doesn't exist
            if "/metadata/models" not in f:
                logger.info(
                    "MEMORY_MIGRATION_MODELS_DATASET",
                    doctor_id=self.doctor_id,
                    message="Creating models dataset for existing H5 file",
                )
                current_size = f["/embeddings/vectors"].shape[0]
                f["/metadata"].create_dataset(
                    "models",
                    shape=(current_size,),
                    maxshape=(None,),
                    dtype=h5py.string_dtype(encoding="utf-8", length=64),
                    chunks=(1000,),
                    data=[""] * current_size,  # Fill existing entries with empty string
                )

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
            f["/metadata/models"].resize((new_size,))

            # Append data
            f["/embeddings/vectors"][current_size] = embedding
            f["/metadata/session_ids"][current_size] = session_id
            f["/metadata/timestamps"][current_size] = timestamp
            f["/metadata/roles"][current_size] = role
            f["/metadata/content"][current_size] = content[:4096]  # Truncate if needed
            f["/metadata/personas"][current_size] = persona or ""
            f["/metadata/models"][current_size] = model or ""

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

    async def get_context(
        self,
        current_message: str,
        session_id: str | None = None,
    ) -> ConversationContext:
        """Retrieve conversation context for LLM prompt.

        Implements hierarchical retrieval:
        1. Recent context: Last N interactions (from current session if specified)
        2. Relevant context: Top-K semantically similar interactions (cross-session)

        Query embedding is computed by FI Monitor (async HTTP call).

        Args:
            current_message: Current user message (for semantic search)
            session_id: Optional session filter for recent context

        Returns:
            ConversationContext with recent + relevant interactions
        """
        start_time = time.time()

        # Get embedding for current message from FI Monitor
        embeddings = await get_embeddings_from_fi([current_message])
        query_embedding = embeddings[0]

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
            stored_embeddings = f["/embeddings/vectors"][:]  # (N, _embedding_dim)
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
            # Load models (with migration support for old H5 files)
            if "/metadata/models" in f:
                models = [
                    m.decode("utf-8") if isinstance(m, bytes) else str(m)
                    for m in f["/metadata/models"][:]  # type: ignore[union-attr]
                ]
            else:
                # Old H5 file without models - use empty strings
                models = [""] * len(session_ids)

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
                        embedding=stored_embeddings[idx],
                        persona=personas[idx] if personas[idx] else None,
                        model=models[idx] if models[idx] else None,
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
                    embedding=stored_embeddings[idx],
                    persona=personas[idx] if personas[idx] else None,
                    model=models[idx] if models[idx] else None,
                )
                for idx in recent_indices
            ]

        # 2. Get relevant context (semantic search, excluding recent)
        recent_indices_set = {int(i.interaction_idx) for i in recent}

        # Compute cosine similarity (vectorized)
        # scores = embeddings @ query / (||embeddings|| * ||query||)
        norms = np.linalg.norm(stored_embeddings, axis=1)  # type: ignore[call-overload]
        query_norm = np.linalg.norm(query_embedding)
        similarities = stored_embeddings @ query_embedding / (norms * query_norm)

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
                embedding=stored_embeddings[idx],
                persona=personas[idx] if personas[idx] else None,
                model=models[idx] if models[idx] else None,
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
                "doctor_id": self.doctor_id,
            }

        with h5py.File(self.memory_path, "r") as f:
            total = f["/embeddings/vectors"].shape[0]
            if total == 0:
                return {
                    "total_interactions": 0,
                    "unique_sessions": 0,
                    "memory_index_exists": True,
                    "doctor_id": self.doctor_id,
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
            # Load models (with migration support for old H5 files)
            if "/metadata/models" in f:
                models = [
                    m.decode("utf-8") if isinstance(m, bytes) else str(m)
                    for m in f["/metadata/models"][:]  # type: ignore[union-attr]
                ]
            else:
                # Old H5 file without models - use empty strings
                models = [""] * len(session_ids)
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
                    model=models[idx] if models[idx] else None,
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


def get_memory_manager(doctor_id: str) -> ConversationMemoryManager | None:
    """Get singleton memory manager for doctor.

    Args:
        doctor_id: Doctor identifier

    Returns:
        ConversationMemoryManager instance for doctor, or None if embeddings unavailable
    """
    global _memory_managers

    # Return None if FI Monitor not configured (embeddings unavailable)
    if not is_embeddings_available():
        return None

    if doctor_id not in _memory_managers:
        with _manager_lock:
            # Double-check inside lock
            if doctor_id not in _memory_managers:
                _memory_managers[doctor_id] = ConversationMemoryManager(doctor_id)

    return _memory_managers[doctor_id]
