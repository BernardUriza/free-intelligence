"""Service layer for evidence pack operations.

Handles creation, retrieval, and management of evidence packs.
Encapsulates evidence pack building and storage operations.

Clean Code: This service layer makes endpoints simple and focused.
"""

from __future__ import annotations

from typing import Any

from backend.evidence_pack import EvidencePackBuilder, create_evidence_pack_from_sources
from backend.logger import get_logger

logger = get_logger(__name__)


class EvidenceService:
    """Service for evidence pack operations.

    Orchestrates evidence pack creation, retrieval, and filtering.
    Handles:
    - Evidence pack creation from clinical sources
    - Pack storage and retrieval
    - Session-based filtering
    - Pack metadata management
    """

    def __init__(self) -> None:
        """Initialize service with in-memory store."""
        self._evidence_store: dict[str, dict] = {}
        logger.info("EvidenceService initialized")

    def create_evidence_pack(
        self,
        sources: list[dict[str, Any]],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create evidence pack from clinical sources.

        Args:
            sources: List of clinical source dictionaries
            session_id: Optional session identifier

        Returns:
            Evidence pack response dict with pack_id, metadata, etc.

        Raises:
            ValueError: If validation fails
        """
        if not sources:
            raise ValueError("At least one source is required")

        try:
            # Create pack using existing builder
            pack = create_evidence_pack_from_sources(sources, session_id=session_id)

            # Store pack
            builder = EvidencePackBuilder()
            pack_dict = builder.to_dict(pack)
            self._evidence_store[pack.pack_id] = pack_dict

            logger.info(
                f"EVIDENCE_PACK_CREATED: pack_id={pack.pack_id}, source_count={len(pack.sources)}, session_id={session_id}"
            )

            return {
                "pack_id": pack.pack_id,
                "created_at": pack.created_at,
                "session_id": pack.session_id,
                "source_count": len(pack.sources),
                "source_hashes": pack.source_hashes,
                "policy_snapshot_id": pack.policy_snapshot_id,
                "metadata": pack.metadata,
            }

        except Exception as e:
            logger.error(f"EVIDENCE_PACK_CREATION_FAILED: error={str(e)}")
            raise ValueError(f"Failed to create evidence pack: {str(e)}") from e

    def get_evidence_pack(self, pack_id: str) -> dict[str, Any | None] | None:
        """Get evidence pack by ID.

        Args:
            pack_id: Pack identifier

        Returns:
            Evidence pack dict or None if not found
        """
        if pack_id not in self._evidence_store:
            logger.warning(f"EVIDENCE_PACK_NOT_FOUND: pack_id={pack_id}")
            return None

        pack_dict = self._evidence_store[pack_id]
        logger.info(f"EVIDENCE_PACK_RETRIEVED: pack_id={pack_id}")

        return {
            "pack_id": pack_dict["pack_id"],
            "created_at": pack_dict["created_at"],
            "session_id": pack_dict.get("session_id"),
            "source_count": pack_dict["metadata"].get("source_count", 0),
            "source_hashes": pack_dict.get("source_hashes", []),
            "policy_snapshot_id": pack_dict.get("policy_snapshot_id"),
            "metadata": pack_dict.get("metadata", {}),
        }

    def get_session_evidence(self, session_id: str) -> list[dict[str, Any]]:
        """Get all evidence packs for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of evidence pack dicts matching session
        """
        session_packs = [
            pack for pack in self._evidence_store.values() if pack.get("session_id") == session_id
        ]

        logger.info(
            f"SESSION_EVIDENCE_RETRIEVED: session_id={session_id}, pack_count={len(session_packs)}"
        )

        return [
            {
                "pack_id": pack["pack_id"],
                "created_at": pack["created_at"],
                "session_id": pack.get("session_id"),
                "source_count": pack["metadata"].get("source_count", 0),
                "source_hashes": pack.get("source_hashes", []),
                "policy_snapshot_id": pack.get("policy_snapshot_id"),
                "metadata": pack.get("metadata", {}),
            }
            for pack in session_packs
        ]

    def list_all_packs(self) -> list[dict[str, Any]]:
        """List all evidence packs.

        Returns:
            List of all evidence pack dicts
        """
        packs = list(self._evidence_store.values())
        logger.info(f"EVIDENCE_PACKS_LISTED: count={len(packs)}")

        return [
            {
                "pack_id": pack["pack_id"],
                "created_at": pack["created_at"],
                "session_id": pack.get("session_id"),
                "source_count": pack["metadata"].get("source_count", 0),
                "source_hashes": pack.get("source_hashes", []),
                "policy_snapshot_id": pack.get("policy_snapshot_id"),
                "metadata": pack.get("metadata", {}),
            }
            for pack in packs
        ]

    def delete_evidence_pack(self, pack_id: str) -> bool:
        """Delete evidence pack by ID.

        Args:
            pack_id: Pack identifier

        Returns:
            True if deleted, False if not found
        """
        if pack_id not in self._evidence_store:
            logger.warning(f"EVIDENCE_PACK_DELETE_NOT_FOUND: pack_id={pack_id}")
            return False

        del self._evidence_store[pack_id]
        logger.info(f"EVIDENCE_PACK_DELETED: pack_id={pack_id}")
        return True
