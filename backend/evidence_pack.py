"""Evidence pack module - wrapper for fi_common.

Re-exports from packages.fi_common.infrastructure.evidence_pack for backward compatibility.
"""

from __future__ import annotations

from packages.fi_common.infrastructure.evidence_pack import (
    ClinicalSource,
    EvidencePack,
    EvidencePackBuilder,
    create_evidence_pack_from_sources,
)

__all__ = [
    "ClinicalSource",
    "EvidencePack",
    "EvidencePackBuilder",
    "create_evidence_pack_from_sources",
]
