#!/usr/bin/env python3
"""
Tests for Evidence Pack Builder

File: tests/test_evidence_pack.py
Card: FI-DATA-RES-021
"""

import unittest

from backend.evidence_pack import (
    ClinicalSource,
    EvidencePackBuilder,
    create_evidence_pack_from_sources,
)


class TestClinicalSource(unittest.TestCase):
    """Tests for ClinicalSource dataclass"""

    def test_create_minimal_source(self) -> None:
        """Test creating source with minimum required fields"""
        source = ClinicalSource(
            source_id="abc123",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )

        self.assertEqual(source.source_id, "abc123")
        self.assertEqual(source.tipo_doc, "cita_medica")
        self.assertIsNone(source.hallazgo)

    def test_create_full_source(self) -> None:
        """Test creating source with all fields"""
        source = ClinicalSource(
            source_id="abc123",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
            hallazgo="Diabetes tipo 2",
            severidad="moderado",
            raw_text="Patient presents with...",
        )

        self.assertEqual(source.hallazgo, "Diabetes tipo 2")
        self.assertEqual(source.severidad, "moderado")


class TestEvidencePackBuilder(unittest.TestCase):
    """Tests for EvidencePackBuilder"""

    def setUp(self) -> None:
        """Set up builder for tests"""
        self.builder = EvidencePackBuilder()

    def test_builder_initialization(self) -> None:
        """Test builder initializes correctly"""
        self.assertIsNotNone(self.builder.config)
        self.assertEqual(len(self.builder.sources), 0)

    def test_add_single_source(self) -> None:
        """Test adding single source"""
        source = ClinicalSource(
            source_id="test1",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )

        self.builder.add_source(source)
        self.assertEqual(len(self.builder.sources), 1)

    def test_add_multiple_sources(self) -> None:
        """Test adding multiple sources"""
        for i in range(3):
            source = ClinicalSource(
                source_id=f"test{i}",
                tipo_doc="cita_medica",
                fecha="2025-10-30",
                paciente_id=f"patient_{i:03d}",
            )
            self.builder.add_source(source)

        self.assertEqual(len(self.builder.sources), 3)

    def test_compute_source_hash(self) -> None:
        """Test SHA256 hash computation"""
        source = ClinicalSource(
            source_id="test1",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )

        hash1 = self.builder.compute_source_hash(source)
        hash2 = self.builder.compute_source_hash(source)

        # Hash should be deterministic
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 is 64 hex chars

    def test_hash_uniqueness(self) -> None:
        """Test that different sources produce different hashes"""
        source1 = ClinicalSource(
            source_id="test1",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )

        source2 = ClinicalSource(
            source_id="test2",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_002",
        )

        hash1 = self.builder.compute_source_hash(source1)
        hash2 = self.builder.compute_source_hash(source2)

        self.assertNotEqual(hash1, hash2)

    def test_build_pack_from_sources(self) -> None:
        """Test building evidence pack from 5 sources"""
        # Add 5 dummy sources
        for i in range(5):
            source = ClinicalSource(
                source_id=f"source_{i}",
                tipo_doc="cita_medica",
                fecha="2025-10-30",
                paciente_id=f"patient_{i:03d}",
                hallazgo=f"Finding {i}",
            )
            self.builder.add_source(source)

        pack = self.builder.build(session_id="session_test_001")

        # Verify pack structure
        self.assertIsNotNone(pack.pack_id)
        self.assertIsNotNone(pack.created_at)
        self.assertEqual(pack.session_id, "session_test_001")
        self.assertEqual(len(pack.sources), 5)
        self.assertEqual(len(pack.source_hashes), 5)
        self.assertEqual(pack.metadata["source_count"], 5)

    def test_build_fails_without_sources(self) -> None:
        """Test that build fails if no sources added"""
        with self.assertRaises(ValueError):
            self.builder.build()

    def test_pack_to_dict(self) -> None:
        """Test converting pack to dictionary"""
        source = ClinicalSource(
            source_id="test1",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )
        self.builder.add_source(source)

        pack = self.builder.build()
        pack_dict = self.builder.to_dict(pack)

        # Verify dictionary structure
        self.assertIn("pack_id", pack_dict)
        self.assertIn("created_at", pack_dict)
        self.assertIn("sources", pack_dict)
        self.assertIn("source_hashes", pack_dict)
        self.assertIn("policy_snapshot_id", pack_dict)
        self.assertIsInstance(pack_dict["sources"], list)

    def test_pack_to_json(self) -> None:
        """Test converting pack to JSON"""
        source = ClinicalSource(
            source_id="test1",
            tipo_doc="cita_medica",
            fecha="2025-10-30",
            paciente_id="patient_001",
        )
        self.builder.add_source(source)

        pack = self.builder.build()
        json_str = self.builder.to_json(pack)

        # Verify JSON is valid
        self.assertIsInstance(json_str, str)
        self.assertIn('"pack_id"', json_str)
        self.assertIn('"source_hashes"', json_str)


class TestConvenienceFunction(unittest.TestCase):
    """Tests for convenience function"""

    def test_create_pack_from_dicts(self) -> None:
        """Test creating pack from source dictionaries"""
        sources = [
            {
                "source_id": f"source_{i}",
                "tipo_doc": "cita_medica",
                "fecha": "2025-10-30",
                "paciente_id": f"patient_{i:03d}",
            }
            for i in range(5)
        ]

        pack = create_evidence_pack_from_sources(sources, session_id="test_session")

        self.assertEqual(len(pack.sources), 5)
        self.assertEqual(pack.session_id, "test_session")
        self.assertEqual(len(pack.source_hashes), 5)


if __name__ == "__main__":
    unittest.main()
