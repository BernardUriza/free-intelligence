"""Evidence pack module - re-exports from fi_common for backward compatibility."""

from __future__ import annotations

from fi_common.infrastructure.evidence_pack import (
    EvidencePackBuilder,
    create_evidence_pack_from_sources,
)

__all__ = ["EvidencePackBuilder", "create_evidence_pack_from_sources"]