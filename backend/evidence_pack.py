#!/usr/bin/env python3
"""
Free Intelligence - Evidence Pack Builder

Creates evidence packs from clinical sources with SHA256 hashes and policy tracking.

File: backend/evidence_pack.py
Card: FI-DATA-RES-021
Created: 2025-10-30

Philosophy:
- Every evidence pack is immutable once created
- Source documents tracked by SHA256
- Policy snapshots for audit trail
- Pack = citas + hashes + source_ids + policy_snapshot_id
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ClinicalSource:
    """Clinical source document"""

    source_id: str  # SHA256 of source file
    tipo_doc: str  # Document type
    fecha: str  # ISO-8601 date
    paciente_id: str  # Patient ID (hashed)
    hallazgo: Optional[str] = None  # Clinical finding
    severidad: Optional[str] = None  # Severity
    raw_text: Optional[str] = None  # Original text


@dataclass
class EvidencePack:
    """Evidence pack with clinical sources"""

    pack_id: str  # Unique pack identifier
    created_at: str  # ISO-8601 timestamp
    session_id: Optional[str]  # Associated session
    sources: list[ClinicalSource]  # Clinical sources
    source_hashes: list[str]  # SHA256 of each source
    policy_snapshot_id: str  # Policy version at creation
    metadata: dict  # Additional metadata


class EvidencePackBuilder:
    """Builder for creating evidence packs"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize evidence pack builder.

        Args:
            config_path: Path to clinical extraction config (default: config/extract/clinical_min.yaml)
        """
        if config_path is None:
            config_path = Path("config/extract/clinical_min.yaml")

        self.config = self._load_config(config_path)
        self.sources: list[ClinicalSource] = []

    def _load_config(self, path: Path) -> dict:
        """Load extraction configuration"""
        if not path.exists():
            # Return default config if file doesn't exist
            return {
                "version": "1.0",
                "extraction": {"max_documents": 100, "hash_algorithm": "sha256"},
            }

        with open(path) as f:
            return yaml.safe_load(f)

    def add_source(self, source: ClinicalSource) -> "EvidencePackBuilder":
        """
        Add clinical source to pack.

        Args:
            source: Clinical source document

        Returns:
            Self for chaining
        """
        max_docs = self.config.get("extraction", {}).get("max_documents", 100)

        if len(self.sources) >= max_docs:
            raise ValueError(f"Maximum documents ({max_docs}) exceeded")

        self.sources.append(source)
        return self

    def compute_source_hash(self, source: ClinicalSource) -> str:
        """
        Compute SHA256 hash of source document.

        Args:
            source: Clinical source

        Returns:
            SHA256 hash (hex)
        """
        # Hash deterministic representation
        content = json.dumps(asdict(source), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def build(self, session_id: Optional[str] = None, policy_version: str = "v1.0") -> EvidencePack:
        """
        Build evidence pack from sources.

        Args:
            session_id: Optional session ID to associate
            policy_version: Policy snapshot identifier

        Returns:
            Immutable evidence pack
        """
        if not self.sources:
            raise ValueError("No sources added to pack")

        # Generate pack ID
        timestamp = int(time.time())
        pack_id = f"pack_{timestamp}_{len(self.sources)}"

        # Compute hashes for all sources
        source_hashes = [self.compute_source_hash(src) for src in self.sources]

        # Create pack
        pack = EvidencePack(
            pack_id=pack_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            session_id=session_id,
            sources=self.sources,
            source_hashes=source_hashes,
            policy_snapshot_id=policy_version,
            metadata={
                "source_count": len(self.sources),
                "document_types": list(set(src.tipo_doc for src in self.sources)),
                "hash_algorithm": "sha256",
            },
        )

        return pack

    def to_dict(self, pack: EvidencePack) -> dict:
        """
        Convert evidence pack to dictionary.

        Args:
            pack: Evidence pack

        Returns:
            Dictionary representation
        """
        return {
            "pack_id": pack.pack_id,
            "created_at": pack.created_at,
            "session_id": pack.session_id,
            "sources": [asdict(src) for src in pack.sources],
            "source_hashes": pack.source_hashes,
            "policy_snapshot_id": pack.policy_snapshot_id,
            "metadata": pack.metadata,
        }

    def to_json(self, pack: EvidencePack) -> str:
        """
        Convert evidence pack to JSON.

        Args:
            pack: Evidence pack

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(pack), indent=2)


def create_evidence_pack_from_sources(
    sources: list[dict], session_id: Optional[str] = None
) -> EvidencePack:
    """
    Convenience function to create evidence pack from source dictionaries.

    Args:
        sources: List of source dictionaries
        session_id: Optional session ID

    Returns:
        Evidence pack
    """
    builder = EvidencePackBuilder()

    for src_dict in sources:
        source = ClinicalSource(**src_dict)
        builder.add_source(source)

    return builder.build(session_id=session_id)
