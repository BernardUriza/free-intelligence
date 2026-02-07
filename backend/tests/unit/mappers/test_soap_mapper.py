"""Tests for SOAPMapper (P1-5 Repository Mappers).

Validates bidirectional mapping between SOAPNote domain entities and HDF5 persistence.

Author: Claude Code (P3-3 Testing Infrastructure)
Created: 2026-02-02
"""

from __future__ import annotations

import pytest

from backend.domain.soap.models import (
    AssessmentData,
    ObjectiveData,
    PlanData,
    SOAPNote,
    SubjectiveData,
)
from backend.mappers.soap_mapper import (
    SOAPHDF5Content,
    SOAPHDF5Metadata,
    SOAPMapper,
)


class TestSOAPMapperToHDF5:
    """Test SOAPMapper.to_hdf5() conversion."""

    def test_to_hdf5_converts_soap_note_correctly(self):
        """SOAPMapper.to_hdf5() should convert SOAPNote to HDF5 structures."""
        # Arrange
        soap = SOAPNote(
            subjective=SubjectiveData(
                chief_complaint="Dolor de cabeza",
                history_present_illness="Dolor desde hace 3 días",
                past_medical_history="Hipertensión controlada",
            ),
            objective=ObjectiveData(
                vital_signs="BP: 120/80, HR: 72",
                physical_exam="Neurológico normal",
            ),
            assessment=AssessmentData(
                differential_diagnoses=["Migraña", "Cefalea tensional"],
                primary_diagnosis="Migraña sin aura",
            ),
            plan=PlanData(
                treatment="Ibuprofeno 400mg c/8h",
                follow_up="Control en 7 días",
                studies=["Ninguno indicado"],
            ),
        )
        # Add dynamic fields (extra="allow")
        soap.soap_id = "soap_123"
        soap.session_id = "session_456"
        soap.created_at = "2026-02-02T10:00:00Z"

        # Act
        metadata, content = SOAPMapper.to_hdf5(soap)

        # Assert
        assert isinstance(metadata, SOAPHDF5Metadata)
        assert metadata.soap_id == "soap_123"
        assert metadata.session_id == "session_456"
        assert metadata.created_at == "2026-02-02T10:00:00Z"

        assert isinstance(content, SOAPHDF5Content)
        assert content.subjective["chief_complaint"] == "Dolor de cabeza"
        assert content.objective["vital_signs"] == "BP: 120/80, HR: 72"
        assert content.assessment["primary_diagnosis"] == "Migraña sin aura"
        assert content.plan["treatment"] == "Ibuprofeno 400mg c/8h"

    def test_to_hdf5_raises_on_missing_soap_id(self):
        """SOAPMapper.to_hdf5() should raise ValueError if soap_id is missing."""
        # Arrange
        soap = SOAPNote(
            subjective=SubjectiveData(
                chief_complaint="Test",
                history_present_illness="Test",
                past_medical_history="Test",
            ),
            objective=ObjectiveData(vital_signs="Test", physical_exam="Test"),
            assessment=AssessmentData(primary_diagnosis="Test"),
            plan=PlanData(treatment="Test", follow_up="Test"),
        )
        # Missing soap.soap_id

        # Act & Assert
        with pytest.raises(ValueError, match="soap_id is required"):
            SOAPMapper.to_hdf5(soap)


class TestSOAPMapperFromHDF5:
    """Test SOAPMapper.from_hdf5() conversion."""

    def test_from_hdf5_converts_to_soap_note_correctly(self):
        """SOAPMapper.from_hdf5() should convert HDF5 structures to SOAPNote."""
        # Arrange
        metadata = SOAPHDF5Metadata(
            soap_id="soap_123",
            session_id="session_456",
            created_at="2026-02-02T10:00:00Z",
            status="draft",
        )

        content = SOAPHDF5Content(
            subjective={
                "chief_complaint": "Dolor de cabeza",
                "history_present_illness": "Dolor desde hace 3 días",
                "past_medical_history": "Hipertensión",
            },
            objective={
                "vital_signs": "BP: 120/80",
                "physical_exam": "Normal",
            },
            assessment={
                "differential_diagnoses": ["Migraña", "Tensional"],
                "primary_diagnosis": "Migraña",
            },
            plan={
                "treatment": "Ibuprofeno",
                "follow_up": "7 días",
                "studies": [],
            },
        )

        # Act
        soap = SOAPMapper.from_hdf5("soap_123", metadata, content)

        # Assert
        assert isinstance(soap, SOAPNote)
        assert soap.subjective.chief_complaint == "Dolor de cabeza"
        assert soap.objective.vital_signs == "BP: 120/80"
        assert soap.assessment.primary_diagnosis == "Migraña"
        assert soap.plan.treatment == "Ibuprofeno"

        # Check dynamic fields
        assert soap.soap_id == "soap_123"
        assert soap.session_id == "session_456"
        assert soap.created_at == "2026-02-02T10:00:00Z"

    def test_from_hdf5_raises_on_soap_id_mismatch(self):
        """SOAPMapper.from_hdf5() should raise ValueError if soap_id doesn't match."""
        # Arrange
        metadata = SOAPHDF5Metadata(
            soap_id="soap_999",  # Mismatch!
            session_id="session_456",
            created_at="2026-02-02T10:00:00Z",
        )
        content = SOAPHDF5Content(
            subjective={"chief_complaint": "Test", "history_present_illness": "Test", "past_medical_history": "Test"},
            objective={"vital_signs": "Test", "physical_exam": "Test"},
            assessment={"differential_diagnoses": [], "primary_diagnosis": "Test"},
            plan={"treatment": "Test", "follow_up": "Test", "studies": []},
        )

        # Act & Assert
        with pytest.raises(ValueError, match="soap_id mismatch"):
            SOAPMapper.from_hdf5("soap_123", metadata, content)


class TestSOAPMapperRoundTrip:
    """Test bidirectional conversion (round-trip)."""

    def test_round_trip_preserves_data(self):
        """Converting SOAPNote → HDF5 → SOAPNote should preserve all data."""
        # Arrange
        original_soap = SOAPNote(
            subjective=SubjectiveData(
                chief_complaint="Dolor abdominal",
                history_present_illness="Dolor epigástrico desde anoche",
                past_medical_history="Gastritis previa",
            ),
            objective=ObjectiveData(
                vital_signs="BP: 130/85, HR: 78, Temp: 37.2°C",
                physical_exam="Abdomen doloroso a la palpación epigástrica",
            ),
            assessment=AssessmentData(
                differential_diagnoses=["Gastritis aguda", "Úlcera péptica", "Pancreatitis"],
                primary_diagnosis="Gastritis aguda",
            ),
            plan=PlanData(
                treatment="Omeprazol 40mg/día, dieta blanda",
                follow_up="Re-evaluación en 5 días o si empeora",
                studies=["Endoscopía si no mejora en 1 semana"],
            ),
        )
        original_soap.soap_id = "soap_789"
        original_soap.session_id = "session_101"
        original_soap.created_at = "2026-02-02T15:30:00Z"
        original_soap.status = "final"

        # Act: Round-trip conversion
        metadata, content = SOAPMapper.to_hdf5(original_soap)
        reconstructed_soap = SOAPMapper.from_hdf5("soap_789", metadata, content)

        # Assert: All fields preserved
        assert reconstructed_soap.soap_id == original_soap.soap_id
        assert reconstructed_soap.session_id == original_soap.session_id
        assert reconstructed_soap.subjective.chief_complaint == original_soap.subjective.chief_complaint
        assert reconstructed_soap.objective.vital_signs == original_soap.objective.vital_signs
        assert reconstructed_soap.assessment.primary_diagnosis == original_soap.assessment.primary_diagnosis
        assert reconstructed_soap.plan.treatment == original_soap.plan.treatment
        assert len(reconstructed_soap.assessment.differential_diagnoses) == 3
        assert reconstructed_soap.plan.studies == ["Endoscopía si no mejora en 1 semana"]
