#!/usr/bin/env python3
from __future__ import annotations

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
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class Citation:
    """Citation reference for evidence"""

    citation_id: int  # Numeric ID for citation (e.g., [1], [2])
    source_id: str  # Source document ID
    text: str  # Exact text being cited
    page_number: Optional[int] = None  # Page reference if available
    confidence: float = 1.0  # Confidence score for extraction


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
    citations: Optional[List[Citation]] = None  # Associated citations


@dataclass
class EvidencePack:
    """Evidence pack with clinical sources"""

    pack_id: str  # Unique pack identifier
    created_at: str  # ISO-8601 timestamp
    session_id: Optional[str]  # Associated session
    sources: List[ClinicalSource]  # Clinical sources
    source_hashes: List[str]  # SHA256 of each source
    policy_snapshot_id: str  # Policy version at creation
    metadata: Dict  # Additional metadata
    citations: Optional[List[Citation]] = None  # All citations in pack
    consulta: Optional[str] = None  # Clinical question being answered
    response: Optional[str] = None  # Generated response with citations only


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
        self.sources: List[ClinicalSource] = []
        self.citations: List[Citation] = []
        self.citation_counter: int = 1
        self.consulta: Optional[str] = None

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

    def add_source(self, source: ClinicalSource) -> EvidencePackBuilder:
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

    def set_consulta(self, consulta: str) -> EvidencePackBuilder:
        """
        Set the clinical question being addressed.

        Args:
            consulta: Clinical question

        Returns:
            Self for chaining
        """
        self.consulta = consulta
        return self

    def extract_citations(self, source: ClinicalSource) -> List[Citation]:
        """
        Extract citations from a clinical source.

        Args:
            source: Clinical source to extract citations from

        Returns:
            List of citations
        """
        citations = []

        # Extract citation from hallazgo (clinical finding)
        if source.hallazgo:
            citation = Citation(
                citation_id=self.citation_counter,
                source_id=source.source_id,
                text=source.hallazgo[:200],  # Limit citation text length
                confidence=0.95,
            )
            citations.append(citation)
            self.citations.append(citation)
            self.citation_counter += 1

        # Extract from raw text if available
        if source.raw_text and len(source.raw_text) > 50:
            # Extract key sentences (simplified - in production use NLP)
            sentences = source.raw_text.split(".")[:3]  # First 3 sentences
            for sentence in sentences:
                if len(sentence.strip()) > 20:  # Meaningful sentence
                    citation = Citation(
                        citation_id=self.citation_counter,
                        source_id=source.source_id,
                        text=sentence.strip()[:200],
                        confidence=0.85,
                    )
                    citations.append(citation)
                    self.citations.append(citation)
                    self.citation_counter += 1

        return citations

    def generate_response(self) -> str:
        """
        Generate Q&A response with citations only (no diagnosis).

        Returns:
            Response text with citation references
        """
        if not self.sources:
            return "No se encontraron datos relevantes para la consulta."

        response_parts = []

        # Add query
        if self.consulta:
            response_parts.append(f"**Consulta**: {self.consulta}\n")

        response_parts.append("**Evidencia encontrada**:\n")

        # Group citations by document type
        by_type = {}
        for source in self.sources:
            if source.tipo_doc not in by_type:
                by_type[source.tipo_doc] = []
            by_type[source.tipo_doc].append(source)

        # Format findings with citations
        for tipo_doc, sources in by_type.items():
            response_parts.append(f"\n**{tipo_doc.replace('_', ' ').title()}**:")
            for source in sources:
                if source.hallazgo:
                    # Find citation for this hallazgo
                    citation_refs = []
                    for citation in self.citations:
                        if (
                            citation.source_id == source.source_id
                            and source.hallazgo in citation.text
                        ):
                            citation_refs.append(f"[{citation.citation_id}]")

                    citation_text = " ".join(citation_refs) if citation_refs else ""
                    response_parts.append(f"  - {source.hallazgo} {citation_text}")

        # Add citation references
        response_parts.append("\n**Referencias**:")
        for citation in self.citations:
            response_parts.append(
                f"  [{citation.citation_id}] Documento: {citation.source_id[:8]}... "
                f"(Confianza: {citation.confidence:.0%})"
            )

        # Add disclaimer
        response_parts.append(
            "\n*Nota: Esta respuesta contiene únicamente evidencia extraída de los documentos. "
            "No constituye un diagnóstico médico.*"
        )

        return "\n".join(response_parts)

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

        # Extract citations from all sources
        for source in self.sources:
            source_citations = self.extract_citations(source)
            source.citations = source_citations

        # Generate Q&A response
        response = self.generate_response()

        # Create pack
        pack = EvidencePack(
            pack_id=pack_id,
            created_at=datetime.now(UTC).isoformat() + "Z",
            session_id=session_id,
            sources=self.sources,
            source_hashes=source_hashes,
            policy_snapshot_id=policy_version,
            metadata={
                "source_count": len(self.sources),
                "document_types": list(set(src.tipo_doc for src in self.sources)),
                "hash_algorithm": "sha256",
                "total_citations": len(self.citations),
                "extraction_confidence": sum(c.confidence for c in self.citations)
                / len(self.citations)
                if self.citations
                else 0,
            },
            citations=self.citations,
            consulta=self.consulta,
            response=response,
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
        result = {
            "pack_id": pack.pack_id,
            "created_at": pack.created_at,
            "session_id": pack.session_id,
            "sources": [asdict(src) for src in pack.sources],
            "source_hashes": pack.source_hashes,
            "policy_snapshot_id": pack.policy_snapshot_id,
            "metadata": pack.metadata,
        }

        # Add optional fields if present
        if pack.consulta:
            result["consulta"] = pack.consulta
        if pack.citations:
            result["citations"] = [asdict(c) for c in pack.citations]
        if pack.response:
            result["response"] = pack.response

        return result

    def to_json(self, pack: EvidencePack) -> str:
        """
        Convert evidence pack to JSON.

        Args:
            pack: Evidence pack

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(pack), indent=2, ensure_ascii=False)

    def export_to_file(self, pack: EvidencePack, export_dir: str = "/export/evidence/") -> Path:
        """
        Export evidence pack to JSON file.

        Args:
            pack: Evidence pack to export
            export_dir: Directory to export to (default: /export/evidence/)

        Returns:
            Path to exported file
        """
        # Create export directory if it doesn't exist
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        # Create file path
        file_path = export_path / f"{pack.pack_id}.json"

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json(pack))

        return file_path


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
