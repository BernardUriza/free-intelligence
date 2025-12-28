"""DI Evidence Service - Refactored with dependency injection.

Handles evidence pack operations with injected logger for better testability.
"""

from __future__ import annotations

from typing import Any

from backend.evidence_pack import EvidencePackBuilder
from backend.src.fi_common.interfaces.ilogger import ILogger


class DIEvidenceService:
    """Evidence service with dependency injection.

    Orchestrates evidence pack creation, retrieval, and filtering.
    Handles:
    - Evidence pack creation from clinical sources
    - Pack storage and retrieval
    - Session-based filtering
    - Pack metadata management
    """

    def __init__(self, logger: ILogger) -> None:
        """Initialize service with injected logger.

        Args:
            logger: Logger instance
        """
        self.logger = logger
        self._evidence_store: dict[str, dict] = {}
        self.logger.info("DIEvidenceService initialized")

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
        # Input validation
        if not sources:
            raise ValueError("Sources cannot be empty")

        if not all(isinstance(source, dict) for source in sources):
            raise ValueError("All sources must be dictionaries")

        self.logger.info(
            "EVIDENCE_PACK_CREATION_STARTED",
            session_id=session_id,
            source_count=len(sources),
        )

        try:
            # Create evidence pack using builder
            pack_builder = EvidencePackBuilder()
            pack_id = pack_builder.build_pack(sources, session_id)

            # Get pack metadata
            pack_metadata = pack_builder.get_pack_metadata(pack_id)

            # Store in memory (for now)
            self._evidence_store[pack_id] = {
                "pack_id": pack_id,
                "metadata": pack_metadata,
                "session_id": session_id,
                "created_at": "2025-12-19T00:00:00Z",  # TODO: Use proper timestamp
            }

            self.logger.info(
                "EVIDENCE_PACK_CREATED",
                pack_id=pack_id,
                session_id=session_id,
            )

            return {
                "pack_id": pack_id,
                "metadata": pack_metadata,
                "session_id": session_id,
                "status": "created",
            }

        except Exception as e:
            self.logger.error(
                "EVIDENCE_PACK_CREATION_FAILED",
                session_id=session_id,
                error=str(e),
            )
            raise

    def get_evidence_pack(self, pack_id: str) -> dict[str, Any] | None:
        """Retrieve evidence pack by ID.

        Args:
            pack_id: Evidence pack identifier

        Returns:
            Evidence pack data or None if not found
        """
        pack_data = self._evidence_store.get(pack_id)
        if pack_data:
            self.logger.info("EVIDENCE_PACK_RETRIEVED", pack_id=pack_id)
        else:
            self.logger.warning("EVIDENCE_PACK_NOT_FOUND", pack_id=pack_id)
        return pack_data

    def list_evidence_packs(self, session_id: str | None = None) -> list[dict[str, Any]]:
        """List evidence packs, optionally filtered by session.

        Args:
            session_id: Optional session filter

        Returns:
            List of evidence pack summaries
        """
        packs = []
        for pack_data in self._evidence_store.values():
            if session_id is None or pack_data.get("session_id") == session_id:
                packs.append(
                    {
                        "pack_id": pack_data["pack_id"],
                        "session_id": pack_data.get("session_id"),
                        "created_at": pack_data.get("created_at"),
                        "metadata": pack_data.get("metadata", {}),
                    }
                )

        self.logger.info(
            "EVIDENCE_PACKS_LISTED",
            session_id=session_id,
            count=len(packs),
        )
        return packs
