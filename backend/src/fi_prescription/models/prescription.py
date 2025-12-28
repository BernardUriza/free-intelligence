"""Prescription model representing a complete medical prescription.

A Prescription is an instance of a PrescriptionTemplate filled with
actual patient data, medications, and physician information.

Author: Bernard Uriza Orozco
Created: 2025-12-28
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from fi_prescription.models.medication import Medication
from pydantic import BaseModel, ConfigDict, Field, computed_field


class PrescriptionStatus(str, Enum):
    """Status of a prescription in its lifecycle."""

    DRAFT = "draft"  # Being edited
    PENDING_SIGNATURE = "pending_signature"  # Ready for signature
    SIGNED = "signed"  # Signed by physician
    DISPENSED = "dispensed"  # Dispensed by pharmacy
    CANCELLED = "cancelled"  # Cancelled
    EXPIRED = "expired"  # Past validity date


class PatientInfo(BaseModel):
    """Patient information for the prescription.

    Minimal patient data required for a valid prescription.
    Full patient record is stored separately (fi_patient).
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre completo del paciente",
    )

    age: str | None = Field(
        default=None,
        max_length=20,
        description="Edad del paciente",
        examples=["35 años", "8 meses", "2 años 3 meses"],
    )

    date_of_birth: str | None = Field(
        default=None,
        description="Fecha de nacimiento (YYYY-MM-DD)",
    )

    gender: str | None = Field(
        default=None,
        max_length=20,
        description="Género",
        examples=["Masculino", "Femenino", "Otro"],
    )

    weight_kg: float | None = Field(
        default=None,
        ge=0,
        le=500,
        description="Peso en kilogramos",
    )

    allergies: list[str] = Field(
        default_factory=list,
        description="Alergias conocidas",
    )

    patient_id: str | None = Field(
        default=None,
        description="ID del paciente en el sistema",
    )

    model_config = ConfigDict(extra="allow")


class PhysicianInfo(BaseModel):
    """Physician information for the prescription.

    Contains required fields for Mexican prescription validity.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre completo del médico",
    )

    professional_license: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Cédula profesional",
    )

    specialty: str | None = Field(
        default=None,
        max_length=100,
        description="Especialidad médica",
    )

    specialty_license: str | None = Field(
        default=None,
        max_length=50,
        description="Cédula de especialidad",
    )

    institution: str | None = Field(
        default=None,
        max_length=200,
        description="Institución o consultorio",
    )

    address: str | None = Field(
        default=None,
        max_length=300,
        description="Dirección del consultorio",
    )

    phone: str | None = Field(
        default=None,
        max_length=50,
        description="Teléfono de contacto",
    )

    email: str | None = Field(
        default=None,
        max_length=100,
        description="Correo electrónico",
    )

    physician_id: str | None = Field(
        default=None,
        description="ID del médico en el sistema (Auth0 sub)",
    )

    model_config = ConfigDict(extra="allow")


class Prescription(BaseModel):
    """Complete medical prescription.

    Represents a filled prescription ready for signing and dispensing.
    Contains all information required for a legally valid Mexican prescription.

    Attributes:
        id: Unique prescription identifier
        template_id: Template used to create this prescription
        session_id: Session ID (if linked to a consultation)
        status: Current prescription status
        patient: Patient information
        physician: Physician information
        diagnosis: Primary diagnosis
        diagnosis_code: ICD-10 code (optional)
        medications: List of prescribed medications
        general_instructions: Additional instructions
        validity_days: Days the prescription is valid
        created_at: Creation timestamp
        signed_at: Signature timestamp
        signature_hash: Digital signature hash
        notes: Internal notes (not printed)
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID único de la receta",
    )

    template_id: str = Field(
        default="default",
        description="ID del template utilizado",
    )

    session_id: str | None = Field(
        default=None,
        description="ID de la sesión/consulta asociada",
    )

    status: PrescriptionStatus = Field(
        default=PrescriptionStatus.DRAFT,
        description="Estado de la receta",
    )

    # Patient information
    patient: PatientInfo = Field(
        ...,
        description="Información del paciente",
    )

    # Physician information
    physician: PhysicianInfo = Field(
        ...,
        description="Información del médico",
    )

    # Diagnosis
    diagnosis: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Diagnóstico principal",
    )

    diagnosis_code: str | None = Field(
        default=None,
        max_length=20,
        description="Código CIE-10 del diagnóstico",
        examples=["J06.9", "E11.9", "I10"],
    )

    secondary_diagnoses: list[str] = Field(
        default_factory=list,
        description="Diagnósticos secundarios",
    )

    # Medications
    medications: list[Medication] = Field(
        default_factory=list,
        min_length=1,
        description="Lista de medicamentos prescritos",
    )

    # Additional fields
    general_instructions: str | None = Field(
        default=None,
        max_length=1000,
        description="Indicaciones generales para el paciente",
    )

    next_appointment: str | None = Field(
        default=None,
        max_length=200,
        description="Información de próxima cita",
    )

    # Validity
    validity_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Días de validez de la receta",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de creación",
    )

    signed_at: datetime | None = Field(
        default=None,
        description="Fecha de firma",
    )

    dispensed_at: datetime | None = Field(
        default=None,
        description="Fecha de surtido",
    )

    expires_at: datetime | None = Field(
        default=None,
        description="Fecha de expiración",
    )

    # Integrity
    signature_hash: str | None = Field(
        default=None,
        description="Hash SHA-256 de la receta firmada",
    )

    # Internal notes
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Notas internas (no se imprimen)",
    )

    # Custom fields from template
    custom_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Campos personalizados del template",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "template_id": "default",
                "status": "draft",
                "patient": {
                    "name": "María García López",
                    "age": "45 años",
                    "weight_kg": 68.5,
                    "allergies": ["Penicilina"],
                },
                "physician": {
                    "name": "Dr. Juan Pérez Hernández",
                    "professional_license": "12345678",
                    "specialty": "Medicina Interna",
                },
                "diagnosis": "Infección de vías urinarias no complicada",
                "diagnosis_code": "N39.0",
                "medications": [
                    {
                        "name": "Ciprofloxacino",
                        "dosage": "500mg",
                        "dosage_form": "tableta",
                        "frequency": "every_12_hours",
                        "duration_days": 7,
                        "route": "oral",
                        "quantity": "14 tabletas",
                    }
                ],
                "general_instructions": "Tomar abundantes líquidos. Evitar bebidas alcohólicas.",
                "next_appointment": "En 1 semana si persisten síntomas",
            }
        },
    )

    @computed_field
    @property
    def medication_count(self) -> int:
        """Number of medications in the prescription."""
        return len(self.medications)

    @computed_field
    @property
    def is_signed(self) -> bool:
        """Whether the prescription is signed."""
        return self.status in (
            PrescriptionStatus.SIGNED,
            PrescriptionStatus.DISPENSED,
        )

    @computed_field
    @property
    def is_valid(self) -> bool:
        """Whether the prescription is still valid (not expired/cancelled)."""
        if self.status in (PrescriptionStatus.CANCELLED, PrescriptionStatus.EXPIRED):
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of prescription content.

        Used for integrity verification. Hash includes:
        - Patient name
        - Physician license
        - All medications
        - Diagnosis
        - Created timestamp

        Returns:
            SHA-256 hash string
        """
        content = (
            f"{self.patient.name}|"
            f"{self.physician.professional_license}|"
            f"{self.diagnosis}|"
            f"{self.created_at.isoformat()}|"
        )

        for med in self.medications:
            content += f"{med.name}:{med.dosage}:{med.frequency.value}|"

        return hashlib.sha256(content.encode()).hexdigest()

    def sign(self) -> None:
        """Sign the prescription (mark as signed).

        Sets status to SIGNED, records timestamp, and calculates hash.
        """
        if self.status != PrescriptionStatus.PENDING_SIGNATURE:
            # Allow signing from draft as well
            if self.status != PrescriptionStatus.DRAFT:
                raise ValueError(f"Cannot sign prescription in status: {self.status}")

        self.status = PrescriptionStatus.SIGNED
        self.signed_at = datetime.utcnow()
        self.signature_hash = self.calculate_hash()

        # Calculate expiration
        from datetime import timedelta
        self.expires_at = self.signed_at + timedelta(days=self.validity_days)

    def cancel(self, reason: str | None = None) -> None:
        """Cancel the prescription.

        Args:
            reason: Optional cancellation reason (stored in notes)
        """
        if self.status == PrescriptionStatus.DISPENSED:
            raise ValueError("Cannot cancel a dispensed prescription")

        self.status = PrescriptionStatus.CANCELLED
        if reason:
            self.notes = f"Cancelada: {reason}" + (f"\n{self.notes}" if self.notes else "")

    def mark_dispensed(self) -> None:
        """Mark the prescription as dispensed by pharmacy."""
        if self.status != PrescriptionStatus.SIGNED:
            raise ValueError("Only signed prescriptions can be marked as dispensed")

        self.status = PrescriptionStatus.DISPENSED
        self.dispensed_at = datetime.utcnow()

    def validate_completeness(self) -> list[str]:
        """Validate that prescription has all required fields.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        # Patient validation
        if not self.patient.name.strip():
            errors.append("Nombre del paciente es requerido")

        # Physician validation
        if not self.physician.name.strip():
            errors.append("Nombre del médico es requerido")
        if not self.physician.professional_license.strip():
            errors.append("Cédula profesional es requerida")

        # Diagnosis validation
        if not self.diagnosis.strip():
            errors.append("Diagnóstico es requerido")

        # Medications validation
        if not self.medications:
            errors.append("Al menos un medicamento es requerido")
        else:
            for i, med in enumerate(self.medications, 1):
                if not med.name.strip():
                    errors.append(f"Medicamento {i}: nombre es requerido")
                if not med.dosage.strip():
                    errors.append(f"Medicamento {i}: dosis es requerida")

        return errors

    def to_print_text(self) -> str:
        """Generate plain text version for printing.

        Returns:
            Formatted prescription text following Mexican standards.
        """
        lines: list[str] = []

        # Header
        if self.physician.institution:
            lines.append(self.physician.institution.upper())
        lines.append(f"Dr(a). {self.physician.name}")
        if self.physician.specialty:
            lines.append(self.physician.specialty)
        lines.append(f"Cédula Profesional: {self.physician.professional_license}")
        if self.physician.specialty_license:
            lines.append(f"Cédula de Especialidad: {self.physician.specialty_license}")
        if self.physician.address:
            lines.append(self.physician.address)
        if self.physician.phone:
            lines.append(f"Tel: {self.physician.phone}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("RECETA MÉDICA")
        lines.append("=" * 60)
        lines.append("")

        # Patient info
        lines.append(f"Paciente: {self.patient.name}")
        if self.patient.age:
            lines.append(f"Edad: {self.patient.age}")
        if self.patient.weight_kg:
            lines.append(f"Peso: {self.patient.weight_kg} kg")

        lines.append(f"Fecha: {self.created_at.strftime('%d/%m/%Y')}")
        lines.append("")

        # Diagnosis
        lines.append(f"Diagnóstico: {self.diagnosis}")
        if self.diagnosis_code:
            lines.append(f"CIE-10: {self.diagnosis_code}")
        lines.append("")

        # Medications
        lines.append("-" * 60)
        lines.append("MEDICAMENTOS:")
        lines.append("-" * 60)

        for i, med in enumerate(self.medications, 1):
            lines.append(f"\n{i}. {med.to_prescription_line()}")

        lines.append("")

        # General instructions
        if self.general_instructions:
            lines.append("-" * 60)
            lines.append("INDICACIONES GENERALES:")
            lines.append(self.general_instructions)

        # Next appointment
        if self.next_appointment:
            lines.append("")
            lines.append(f"Próxima cita: {self.next_appointment}")

        # Footer
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        lines.append("")
        lines.append("_" * 40)
        lines.append("Firma del Médico")
        lines.append("")

        if self.signature_hash:
            lines.append(f"Verificación: {self.signature_hash[:16]}...")

        lines.append(f"Válida por {self.validity_days} días a partir de la fecha de emisión")

        return "\n".join(lines)
