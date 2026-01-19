"""
Unit tests for db_models module.
Tests utility functions and model methods.

Coverage targets: backend/models/db_models.py
"""

from __future__ import annotations

from datetime import datetime

import pytest
from backend.models.db_models import Base, Patient, Provider, UserPersonaConfig, generate_uuid


class TestGenerateUuid:
    """Tests for generate_uuid function."""

    def test_generates_string(self):
        """Should generate a string."""
        result = generate_uuid()
        assert isinstance(result, str)

    def test_generates_valid_uuid_format(self):
        """Should generate valid UUID format."""
        result = generate_uuid()
        parts = result.split("-")
        assert len(parts) == 5

    def test_generates_unique_values(self):
        """Should generate unique values."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2


class TestPatientModel:
    """Tests for Patient model."""

    def test_patient_repr(self):
        """Should have proper string representation."""
        patient = Patient()
        patient.nombre = "Juan"
        patient.apellido = "García"
        patient.patient_id = "test-uuid-123"

        repr_str = repr(patient)

        assert "Patient" in repr_str
        assert "Juan" in repr_str
        assert "García" in repr_str

    def test_patient_to_dict(self):
        """Should convert to dictionary."""
        patient = Patient()
        patient.patient_id = "test-uuid-456"
        patient.nombre = "María"
        patient.apellido = "López"
        patient.fecha_nacimiento = datetime(1990, 5, 15)
        patient.genero = None
        patient.curp = "LOPM900515HDFRRL09"
        patient.created_at = datetime(2025, 1, 1, 12, 0, 0)
        patient.updated_at = datetime(2025, 1, 2, 12, 0, 0)

        result = patient.to_dict()

        assert result["patient_id"] == "test-uuid-456"
        assert result["nombre"] == "María"
        assert result["apellido"] == "López"
        assert result["curp"] == "LOPM900515HDFRRL09"

    def test_patient_to_dict_with_null_dates(self):
        """Should handle null dates."""
        patient = Patient()
        patient.patient_id = "test-uuid"
        patient.nombre = "Test"
        patient.apellido = "User"
        patient.fecha_nacimiento = None
        patient.genero = None
        patient.curp = None
        patient.created_at = None
        patient.updated_at = None

        result = patient.to_dict()

        assert result["fecha_nacimiento"] is None
        assert result["created_at"] is None
        assert result["updated_at"] is None


class TestProviderModel:
    """Tests for Provider model."""

    def test_provider_repr(self):
        """Should have proper string representation."""
        provider = Provider()
        provider.nombre = "Dr. Carlos Martínez"
        provider.especialidad = "Cardiología"
        provider.provider_id = "provider-uuid-123"

        repr_str = repr(provider)

        assert "Provider" in repr_str
        assert "Dr. Carlos Martínez" in repr_str
        assert "Cardiología" in repr_str

    def test_provider_to_dict(self):
        """Should convert to dictionary."""
        provider = Provider()
        provider.provider_id = "provider-uuid-456"
        provider.nombre = "Dra. Ana González"
        provider.cedula_profesional = "12345678"
        provider.especialidad = "Medicina Interna"
        provider.created_at = datetime(2025, 1, 1, 12, 0, 0)
        provider.updated_at = datetime(2025, 1, 2, 12, 0, 0)

        result = provider.to_dict()

        assert result["provider_id"] == "provider-uuid-456"
        assert result["nombre"] == "Dra. Ana González"
        assert result["cedula_profesional"] == "12345678"
        assert result["especialidad"] == "Medicina Interna"

    def test_provider_to_dict_with_null_dates(self):
        """Should handle null dates."""
        provider = Provider()
        provider.provider_id = "test-uuid"
        provider.nombre = "Test Provider"
        provider.cedula_profesional = None
        provider.especialidad = None
        provider.created_at = None
        provider.updated_at = None

        result = provider.to_dict()

        assert result["created_at"] is None
        assert result["updated_at"] is None


class TestUserPersonaConfig:
    """Tests for UserPersonaConfig model."""

    def test_user_persona_config_repr(self):
        """Should have proper string representation."""
        config = UserPersonaConfig()
        config.user_id = "user-uuid-123"
        config.persona_id = "soap_editor"
        config.is_active = True

        repr_str = repr(config)

        assert "UserPersonaConfig" in repr_str
        assert "user-uuid-123" in repr_str or "soap_editor" in repr_str

    def test_user_persona_config_to_dict(self):
        """Should convert to dictionary."""
        config = UserPersonaConfig()
        config.user_id = "user-uuid-456"
        config.persona_id = "clinical_advisor"
        config.model = "gpt-4o"
        config.custom_prompt = "You are a helpful medical AI"
        config.temperature = 0.7
        config.max_tokens = 2048
        config.voice = "nova"
        config.is_active = True
        config.created_at = datetime(2025, 1, 1, 12, 0, 0)
        config.updated_at = datetime(2025, 1, 2, 12, 0, 0)

        result = config.to_dict()

        assert result["user_id"] == "user-uuid-456"
        assert result["persona_id"] == "clinical_advisor"
        assert result["model"] == "gpt-4o"
        assert result["temperature"] == 0.7
        assert result["is_active"] is True

    def test_user_persona_config_to_dict_with_nulls(self):
        """Should handle null optional fields."""
        config = UserPersonaConfig()
        config.user_id = "test-uuid"
        config.persona_id = "test_persona"
        config.model = None
        config.custom_prompt = None
        config.temperature = None
        config.max_tokens = None
        config.voice = None
        config.is_active = False
        config.created_at = None
        config.updated_at = None

        result = config.to_dict()

        assert result["model"] is None
        assert result["temperature"] is None
        assert result["created_at"] is None

class TestBaseClass:
    """Tests for Base declarative class."""

    def test_base_exists(self):
        """Base should exist."""
        assert Base is not None

    def test_patient_inherits_base(self):
        """Patient should inherit from Base."""
        assert issubclass(Patient, Base)

    def test_provider_inherits_base(self):
        """Provider should inherit from Base."""
        assert issubclass(Provider, Base)
