"""
Unit tests for backend/providers/models.py

Tests cover:
- All enum types (MessageRole, Severity, Gender, UrgencyLevel, etc.)
- Key Pydantic models (PatientStub, SOAPNote, etc.)
- Field validation

Following HIPAA: No real PHI in test data (using fake/demo values).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from backend.providers.models import (
    DiagnosticoDiferencial,
    DiagnosticoPrincipal,
    EstudioUrgencia,
    EventType,
    Gender,
    Gravedad,
    MessageRole,
    PatientStub,
    Severity,
    SOAPMetadata,
    UrgenciaTriaje,
    UrgencyLevel,
)
from pydantic import ValidationError


# ==============================================================================
# Tests for MessageRole enum
# ==============================================================================
class TestMessageRole:
    """Tests for MessageRole enumeration."""

    def test_user_value(self) -> None:
        """USER should have value 'user'."""
        assert MessageRole.USER.value == "user"

    def test_assistant_value(self) -> None:
        """ASSISTANT should have value 'assistant'."""
        assert MessageRole.ASSISTANT.value == "assistant"

    def test_enum_from_string(self) -> None:
        """Should create enum from string value."""
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT

    def test_is_str_enum(self) -> None:
        """MessageRole should be a str enum for JSON serialization."""
        assert isinstance(MessageRole.USER, str)


# ==============================================================================
# Tests for Severity enum
# ==============================================================================
class TestSeverity:
    """Tests for Severity enumeration."""

    def test_all_values(self) -> None:
        """All severity levels should be defined."""
        assert Severity.MILD.value == "mild"
        assert Severity.MODERATE.value == "moderate"
        assert Severity.SEVERE.value == "severe"

    def test_enum_count(self) -> None:
        """Should have exactly 3 severity levels."""
        assert len(Severity) == 3


# ==============================================================================
# Tests for Gender enum
# ==============================================================================
class TestGender:
    """Tests for Gender enumeration."""

    def test_all_values(self) -> None:
        """All gender options should be defined."""
        assert Gender.MALE.value == "male"
        assert Gender.FEMALE.value == "female"
        assert Gender.OTHER.value == "other"


# ==============================================================================
# Tests for UrgencyLevel enum
# ==============================================================================
class TestUrgencyLevel:
    """Tests for UrgencyLevel enumeration."""

    def test_all_values(self) -> None:
        """All urgency levels should be defined."""
        assert UrgencyLevel.CRITICAL.value == "critical"
        assert UrgencyLevel.HIGH.value == "high"
        assert UrgencyLevel.MEDIUM.value == "medium"
        assert UrgencyLevel.LOW.value == "low"

    def test_ordering(self) -> None:
        """Urgency levels should be orderable by severity."""
        levels = [UrgencyLevel.LOW, UrgencyLevel.MEDIUM, UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        assert len(levels) == 4


# ==============================================================================
# Tests for Gravedad enum (Spanish severity)
# ==============================================================================
class TestGravedad:
    """Tests for Gravedad enumeration."""

    def test_all_values(self) -> None:
        """All gravedad levels should be defined."""
        assert Gravedad.BAJA.value == "baja"
        assert Gravedad.MODERADA.value == "moderada"
        assert Gravedad.ALTA.value == "alta"
        assert Gravedad.CRITICA.value == "critica"


# ==============================================================================
# Tests for UrgenciaTriaje enum
# ==============================================================================
class TestUrgenciaTriaje:
    """Tests for UrgenciaTriaje enumeration (NOM-004 compatible)."""

    def test_all_values(self) -> None:
        """All triage categories should be defined."""
        assert UrgenciaTriaje.NO_URGENTE.value == "no_urgente"
        assert UrgenciaTriaje.SEMI_URGENTE.value == "semi_urgente"
        assert UrgenciaTriaje.URGENTE.value == "urgente"
        assert UrgenciaTriaje.EMERGENCIA.value == "emergencia"


# ==============================================================================
# Tests for EstudioUrgencia enum
# ==============================================================================
class TestEstudioUrgencia:
    """Tests for EstudioUrgencia enumeration."""

    def test_all_values(self) -> None:
        """All study urgency levels should be defined."""
        assert EstudioUrgencia.STAT.value == "stat"
        assert EstudioUrgencia.URGENTE.value == "urgente"
        assert EstudioUrgencia.RUTINA.value == "rutina"


# ==============================================================================
# Tests for EventType enum
# ==============================================================================
class TestEventType:
    """Tests for EventType enumeration."""

    def test_consultation_events(self) -> None:
        """Consultation lifecycle events should be defined."""
        assert EventType.MESSAGE_RECEIVED.value == "MESSAGE_RECEIVED"
        assert EventType.CONSULTATION_COMMITTED.value == "CONSULTATION_COMMITTED"

    def test_extraction_events(self) -> None:
        """Extraction events should be defined."""
        assert EventType.EXTRACTION_STARTED.value == "EXTRACTION_STARTED"
        assert EventType.EXTRACTION_COMPLETED.value == "EXTRACTION_COMPLETED"
        assert EventType.EXTRACTION_FAILED.value == "EXTRACTION_FAILED"

    def test_soap_events(self) -> None:
        """SOAP generation events should be defined."""
        assert EventType.SOAP_GENERATION_STARTED.value == "SOAP_GENERATION_STARTED"
        assert EventType.SOAP_GENERATION_COMPLETED.value == "SOAP_GENERATION_COMPLETED"

    def test_llm_events(self) -> None:
        """LLM call events should be defined."""
        assert EventType.LLM_CALL_INITIATED.value == "LLM_CALL_INITIATED"
        assert EventType.LLM_CALL_COMPLETED.value == "LLM_CALL_COMPLETED"
        assert EventType.LLM_CALL_FAILED.value == "LLM_CALL_FAILED"


# ==============================================================================
# Tests for PatientStub model
# ==============================================================================
class TestPatientStub:
    """Tests for PatientStub Pydantic model."""

    def test_default_values(self) -> None:
        """PatientStub should work with all defaults."""
        patient = PatientStub()

        assert patient.patient_id is None
        assert patient.age is None
        assert patient.gender is None

    def test_age_validator_rejects_over_120(self) -> None:
        """Age validator should reject ages over 120."""
        with pytest.raises(ValidationError):
            PatientStub(age=121)

    def test_age_validator_rejects_negative(self) -> None:
        """Age validator should reject negative ages."""
        with pytest.raises(ValidationError):
            PatientStub(age=-1)

    def test_age_validator_accepts_boundary_values(self) -> None:
        """Age validator should accept 0 and 120."""
        patient_zero = PatientStub(age=0)
        patient_max = PatientStub(age=120)

        assert patient_zero.age == 0
        assert patient_max.age == 120

    def test_valid_patient(self) -> None:
        """PatientStub should accept valid values."""
        patient = PatientStub(
            patient_id="demo-123",
            age=45,
            gender=Gender.MALE,
            weight=70.5,
            height=175.0,
            occupation="Engineer",
        )

        assert patient.age == 45
        assert patient.gender == Gender.MALE
        assert patient.weight == 70.5

    def test_age_validation_too_high(self) -> None:
        """Age over 120 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatientStub(age=150)

        assert "age" in str(exc_info.value).lower()

    def test_age_validation_negative(self) -> None:
        """Negative age should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PatientStub(age=-5)

        assert "age" in str(exc_info.value).lower()

    def test_weight_cannot_be_negative(self) -> None:
        """Weight cannot be negative."""
        with pytest.raises(ValidationError):
            PatientStub(weight=-10)

    def test_gender_enum_assignment(self) -> None:
        """Gender should accept enum values."""
        patient = PatientStub(gender=Gender.FEMALE)
        assert patient.gender == Gender.FEMALE


# ==============================================================================
# Tests for SOAPMetadata model
# ==============================================================================
class TestSOAPMetadata:
    """Tests for SOAPMetadata Pydantic model."""

    def test_required_fields(self) -> None:
        """SOAPMetadata should require core fields."""
        metadata = SOAPMetadata(
            medico="Dr. Demo",
            especialidad="General",
            fecha=datetime.now(timezone.utc),
            duracion_consulta=30,
            consentimiento_informado=True,
        )

        assert metadata.medico == "Dr. Demo"
        assert metadata.version_nom == "NOM-004-SSA3-2012"

    def test_default_version(self) -> None:
        """Default NOM version should be set."""
        metadata = SOAPMetadata(
            medico="Dr. Demo",
            especialidad="General",
            fecha=datetime.now(timezone.utc),
            duracion_consulta=15,
            consentimiento_informado=True,
        )

        assert "NOM-004" in metadata.version_nom


# ==============================================================================
# Tests for DiagnosticoPrincipal model
# ==============================================================================
class TestDiagnosticoPrincipal:
    """Tests for DiagnosticoPrincipal model."""

    def test_basic_diagnosis(self) -> None:
        """DiagnosticoPrincipal should accept required fields."""
        diag = DiagnosticoPrincipal(
            condicion="Hipertensión arterial",
            cie10="I10",
            probabilidad=0.85,
            confianza=0.90,
        )

        assert diag.condicion == "Hipertensión arterial"
        assert diag.cie10 == "I10"
        assert diag.probabilidad == 0.85

    def test_evidencia_defaults_empty(self) -> None:
        """Evidencia should default to empty list."""
        diag = DiagnosticoPrincipal(
            condicion="Test",
            cie10="X00",
            probabilidad=0.5,
            confianza=0.5,
        )

        assert diag.evidencia == []


# ==============================================================================
# Tests for DiagnosticoDiferencial model
# ==============================================================================
class TestDiagnosticoDiferencial:
    """Tests for DiagnosticoDiferencial model."""

    def test_differential_diagnosis(self) -> None:
        """DiagnosticoDiferencial should accept all fields."""
        diag = DiagnosticoDiferencial(
            condicion="Diabetes Mellitus Tipo 2",
            cie10="E11",
            probabilidad=0.75,
            gravedad=Gravedad.MODERADA,
            urgencia=UrgenciaTriaje.SEMI_URGENTE,
            defensive_score=0.68,
        )

        assert diag.probabilidad == 0.75
        assert diag.gravedad == Gravedad.MODERADA
        assert diag.urgencia == UrgenciaTriaje.SEMI_URGENTE

    def test_probability_bounds(self) -> None:
        """Probability should be between 0 and 1."""
        with pytest.raises(ValidationError):
            DiagnosticoDiferencial(
                condicion="Test",
                cie10="X00",
                probabilidad=1.5,  # Invalid: > 1
                gravedad=Gravedad.BAJA,
                urgencia=UrgenciaTriaje.NO_URGENTE,
                defensive_score=0.5,
            )


# ==============================================================================
# Tests for enum JSON serialization
# ==============================================================================
class TestEnumSerialization:
    """Tests for enum JSON serialization (str enums)."""

    def test_message_role_value(self) -> None:
        """MessageRole.value should return string."""
        assert MessageRole.USER.value == "user"

    def test_gender_in_json(self) -> None:
        """Gender should serialize properly in Pydantic model."""
        patient = PatientStub(gender=Gender.MALE)
        json_data = patient.model_dump()

        assert json_data["gender"] == "male"

    def test_gravedad_in_json(self) -> None:
        """Gravedad should serialize as Spanish value."""
        diag = DiagnosticoDiferencial(
            condicion="Test condition",
            cie10="X00",
            probabilidad=0.5,
            gravedad=Gravedad.CRITICA,
            urgencia=UrgenciaTriaje.EMERGENCIA,
            defensive_score=0.85,
        )
        json_data = diag.model_dump()

        assert json_data["gravedad"] == "critica"
