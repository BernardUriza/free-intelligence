"""
Test suite for Evidence Pack functionality
Free Intelligence AURITY - FI-DATA-RES-021

Tests evidence pack creation, citation extraction, and export functionality.
"""

import json

import pytest

# Import the modules under test
from packages.fi_common.infrastructure.evidence_pack import (
    Citation,
    ClinicalSource,
    EvidencePackBuilder,
    create_evidence_pack_from_sources,
)


@pytest.fixture
def sample_clinical_sources():
    """Fixture providing sample clinical sources for testing."""
    return [
        ClinicalSource(
            source_id="doc001",
            tipo_doc="lab_result",
            fecha="2025-11-17",
            paciente_id="patient123_hashed",
            hallazgo="Glucosa en ayunas: 126 mg/dL (elevada)",
            severidad="moderado",
            raw_text="Resultados de laboratorio del paciente. Glucosa en ayunas: 126 mg/dL. Hemoglobina A1c: 7.2%. Colesterol total: 220 mg/dL.",
        ),
        ClinicalSource(
            source_id="doc002",
            tipo_doc="clinical_note",
            fecha="2025-11-16",
            paciente_id="patient123_hashed",
            hallazgo="Presión arterial: 140/90 mmHg",
            severidad="leve",
            raw_text="Paciente presenta hipertensión leve. PA: 140/90 mmHg. Frecuencia cardíaca: 78 lpm.",
        ),
        ClinicalSource(
            source_id="doc003",
            tipo_doc="prescription",
            fecha="2025-11-17",
            paciente_id="patient123_hashed",
            hallazgo="Metformina 850mg cada 12 horas",
            raw_text="Se prescribe Metformina 850mg cada 12 horas para control glucémico.",
        ),
    ]


@pytest.fixture
def builder_with_config(tmp_path):
    """Fixture providing an EvidencePackBuilder with test config."""
    config_path = tmp_path / "test_config.yaml"
    config_content = """
version: "1.0"
extraction:
  max_documents: 100
  hash_algorithm: "sha256"
  min_confidence: 0.7
evidence_pack:
  citation_style: "numeric"
  template_mode: "answer-with-citations-only"
"""
    config_path.write_text(config_content)
    return EvidencePackBuilder(config_path)


class TestEvidencePackBuilder:
    """Test suite for EvidencePackBuilder class."""

    def test_1_builder_initialization(self):
        """Test 1: Builder initializes correctly with default config."""
        builder = EvidencePackBuilder()

        assert builder.sources == []
        assert builder.citations == []
        assert builder.citation_counter == 1
        assert builder.consulta is None
        assert builder.config is not None

    def test_2_add_source_to_builder(self, builder_with_config, sample_clinical_sources):
        """Test 2: Adding sources to builder works correctly."""
        builder = builder_with_config
        source = sample_clinical_sources[0]

        # Add source
        result = builder.add_source(source)

        # Verify chaining works
        assert result == builder
        assert len(builder.sources) == 1
        assert builder.sources[0] == source

    def test_3_extract_citations_from_source(self, builder_with_config, sample_clinical_sources):
        """Test 3: Citation extraction from clinical sources."""
        builder = builder_with_config
        source = sample_clinical_sources[0]

        # Extract citations
        citations = builder.extract_citations(source)

        # Should extract at least one citation from hallazgo
        assert len(citations) > 0
        assert citations[0].source_id == source.source_id
        assert citations[0].citation_id == 1
        assert source.hallazgo in citations[0].text

        # Should also extract from raw_text if available
        total_citations = len(builder.citations)
        assert total_citations >= 2  # At least hallazgo + some from raw_text

    def test_4_generate_qa_response(self, builder_with_config, sample_clinical_sources):
        """Test 4: Q&A response generation with citations only (no diagnosis)."""
        builder = builder_with_config
        builder.set_consulta("¿Cuáles son los valores de glucosa del paciente?")

        # Add all sources
        for source in sample_clinical_sources:
            builder.add_source(source)
            builder.extract_citations(source)

        # Generate response
        response = builder.generate_response()

        # Verify response structure
        assert "**Consulta**:" in response
        assert "**Evidencia encontrada**:" in response
        assert "**Referencias**:" in response
        assert "[1]" in response  # Should have citation references
        assert "No constituye un diagnóstico médico" in response  # Disclaimer

    def test_5_build_evidence_pack(self, builder_with_config, sample_clinical_sources):
        """Test 5: Building complete evidence pack with all components."""
        builder = builder_with_config
        consulta = "¿Cuál es el estado metabólico del paciente?"
        builder.set_consulta(consulta)

        # Add sources
        for source in sample_clinical_sources:
            builder.add_source(source)

        # Build pack
        pack = builder.build(session_id="session_test_123", policy_version="v1.0")

        # Verify pack structure
        assert pack.pack_id is not None
        assert pack.consulta == consulta
        assert len(pack.sources) == 3
        assert len(pack.source_hashes) == 3
        assert pack.policy_snapshot_id == "v1.0"
        assert pack.citations is not None
        assert len(pack.citations) > 0
        assert pack.response is not None
        assert "Glucosa" in pack.response

    def test_6_export_to_json_file(self, builder_with_config, sample_clinical_sources, tmp_path):
        """Test 6: Export evidence pack to JSON file in correct format."""
        builder = builder_with_config
        builder.set_consulta("Test query")

        # Add sources and build pack
        for source in sample_clinical_sources:
            builder.add_source(source)
        pack = builder.build()

        # Export to file
        export_dir = tmp_path / "export" / "evidence"
        file_path = builder.export_to_file(pack, str(export_dir))

        # Verify file exists and contains correct data
        assert file_path.exists()
        assert file_path.name == f"{pack.pack_id}.json"

        # Load and verify JSON content
        with open(file_path, encoding="utf-8") as f:
            exported_data = json.load(f)

        assert exported_data["pack_id"] == pack.pack_id
        assert exported_data["consulta"] == "Test query"
        assert len(exported_data["sources"]) == 3
        assert len(exported_data["source_hashes"]) == 3
        assert "citations" in exported_data
        assert "response" in exported_data

    def test_7_source_hash_computation(self, builder_with_config, sample_clinical_sources):
        """Test 7: SHA256 hash computation for source documents."""
        builder = builder_with_config
        source = sample_clinical_sources[0]

        # Compute hash
        hash1 = builder.compute_source_hash(source)

        # Hash should be deterministic (same input = same hash)
        hash2 = builder.compute_source_hash(source)
        assert hash1 == hash2

        # Hash should be 64 characters (SHA256 in hex)
        assert len(hash1) == 64

        # Different source should produce different hash
        source2 = sample_clinical_sources[1]
        hash3 = builder.compute_source_hash(source2)
        assert hash1 != hash3

    def test_8_create_pack_from_sources_convenience(self, sample_clinical_sources):
        """Test 8: Convenience function creates valid evidence pack from dicts."""
        # Convert sources to dictionaries
        source_dicts = [
            {
                "source_id": src.source_id,
                "tipo_doc": src.tipo_doc,
                "fecha": src.fecha,
                "paciente_id": src.paciente_id,
                "hallazgo": src.hallazgo,
                "severidad": getattr(src, "severidad", None),
                "raw_text": src.raw_text,
            }
            for src in sample_clinical_sources
        ]

        # Create pack using convenience function
        pack = create_evidence_pack_from_sources(
            sources=source_dicts, session_id="test_session_456"
        )

        # Verify pack was created correctly
        assert pack is not None
        assert pack.session_id == "test_session_456"
        assert len(pack.sources) == 3
        assert pack.sources[0].source_id == "doc001"
        assert pack.metadata["source_count"] == 3


class TestCitationClass:
    """Test suite for Citation dataclass."""

    def test_citation_creation(self):
        """Test Citation object creation and attributes."""
        citation = Citation(
            citation_id=1,
            source_id="test_doc",
            text="Sample citation text",
            page_number=5,
            confidence=0.95,
        )

        assert citation.citation_id == 1
        assert citation.source_id == "test_doc"
        assert citation.text == "Sample citation text"
        assert citation.page_number == 5
        assert citation.confidence == 0.95


class TestValidation:
    """Test suite for validation and edge cases."""

    def test_max_documents_limit(self, builder_with_config):
        """Test that max_documents limit is enforced."""
        builder = builder_with_config
        builder.config["extraction"]["max_documents"] = 2

        # Add two sources successfully
        builder.add_source(
            ClinicalSource(
                source_id="doc1",
                tipo_doc="lab_result",
                fecha="2025-11-17",
                paciente_id="patient1",
                hallazgo="Test finding 1",
            )
        )
        builder.add_source(
            ClinicalSource(
                source_id="doc2",
                tipo_doc="lab_result",
                fecha="2025-11-17",
                paciente_id="patient1",
                hallazgo="Test finding 2",
            )
        )

        # Third source should raise error
        with pytest.raises(ValueError, match="Maximum documents"):
            builder.add_source(
                ClinicalSource(
                    source_id="doc3",
                    tipo_doc="lab_result",
                    fecha="2025-11-17",
                    paciente_id="patient1",
                    hallazgo="Test finding 3",
                )
            )

    def test_build_without_sources(self, builder_with_config):
        """Test that building without sources raises error."""
        builder = builder_with_config

        with pytest.raises(ValueError, match="No sources added"):
            builder.build()

    def test_empty_response_generation(self, builder_with_config):
        """Test response generation with no sources."""
        builder = builder_with_config
        builder.set_consulta("Test query")

        response = builder.generate_response()
        assert "No se encontraron datos relevantes" in response


# Integration test
def test_end_to_end_evidence_pack_workflow(tmp_path):
    """Integration test: Complete workflow from sources to exported JSON."""
    # Create test sources
    sources = [
        {
            "source_id": "integration_doc1",
            "tipo_doc": "lab_result",
            "fecha": "2025-11-17",
            "paciente_id": "int_patient",
            "hallazgo": "HbA1c: 7.5% (elevated)",
            "severidad": "moderate",
            "raw_text": "Full lab report showing elevated HbA1c at 7.5%, indicating poor glycemic control over past 3 months.",
        },
        {
            "source_id": "integration_doc2",
            "tipo_doc": "clinical_note",
            "fecha": "2025-11-17",
            "paciente_id": "int_patient",
            "hallazgo": "Patient reports fatigue and thirst",
            "raw_text": "Patient presents with classic diabetes symptoms. Reports increased thirst and frequent urination.",
        },
    ]

    # Create builder
    builder = EvidencePackBuilder()
    builder.set_consulta("What are the patient's diabetes indicators?")

    # Add sources
    for src_dict in sources:
        source = ClinicalSource(**src_dict)
        builder.add_source(source)

    # Build pack
    pack = builder.build(session_id="integration_test", policy_version="v1.0")

    # Export to file
    export_dir = tmp_path / "integration_export"
    file_path = builder.export_to_file(pack, str(export_dir))

    # Verify complete workflow
    assert file_path.exists()

    with open(file_path) as f:
        data = json.load(f)

    assert data["consulta"] == "What are the patient's diabetes indicators?"
    assert len(data["sources"]) == 2
    assert len(data["citations"]) > 0
    assert "HbA1c" in data["response"]
    assert "[1]" in data["response"]  # Has citations
    assert "No constituye un diagnóstico médico" in data["response"]  # Has disclaimer


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])
