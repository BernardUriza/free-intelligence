"""Prescription Template model for customizable prescription layouts.

Templates define:
- Which fields are required/optional
- Default values for institution/physician
- Header/footer content (membrete)
- Field labels and formatting

Author: Bernard Uriza Orozco
Created: 2025-12-28
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FieldType(str, Enum):
    """Types of template fields."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXTAREA = "textarea"
    MEDICATION = "medication"  # Special type for medication entries
    SIGNATURE = "signature"


class TemplateField(BaseModel):
    """Definition of a customizable field in a prescription template.

    Allows physicians/institutions to customize which fields appear
    and how they are configured.

    Attributes:
        key: Unique field identifier
        label: Display label in Spanish
        field_type: Type of input field
        required: Whether field is required
        default_value: Pre-filled default value
        placeholder: Placeholder text
        options: Options for select/multiselect fields
        min_length: Minimum text length
        max_length: Maximum text length
        order: Display order (lower = first)
        visible: Whether field is shown
        help_text: Additional help for the user
    """

    key: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Identificador único del campo (snake_case)",
        examples=["patient_name", "diagnosis", "medications"],
    )

    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Etiqueta visible del campo",
        examples=["Nombre del Paciente", "Diagnóstico", "Medicamentos"],
    )

    field_type: FieldType = Field(
        default=FieldType.TEXT,
        description="Tipo de campo",
    )

    required: bool = Field(
        default=False,
        description="Si el campo es obligatorio",
    )

    default_value: Optional[Any] = Field(
        default=None,
        description="Valor por defecto",
    )

    placeholder: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Texto placeholder",
    )

    options: Optional[list[str]] = Field(
        default=None,
        description="Opciones para campos select/multiselect",
    )

    min_length: Optional[int] = Field(
        default=None,
        ge=0,
        description="Longitud mínima (para texto)",
    )

    max_length: Optional[int] = Field(
        default=None,
        ge=1,
        description="Longitud máxima (para texto)",
    )

    order: int = Field(
        default=0,
        ge=0,
        description="Orden de visualización",
    )

    visible: bool = Field(
        default=True,
        description="Si el campo es visible",
    )

    help_text: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Texto de ayuda para el usuario",
    )

    model_config = ConfigDict(extra="forbid")


class HeaderConfig(BaseModel):
    """Configuration for prescription header (membrete).

    Contains physician/institution information that appears
    at the top of the prescription.
    """

    institution_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nombre de la institución/consultorio",
        examples=["Clínica San Rafael", "Consultorio Dr. García"],
    )

    institution_address: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Dirección completa",
    )

    institution_phone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Teléfono de contacto",
    )

    institution_logo_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL del logo de la institución",
    )

    physician_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nombre completo del médico",
    )

    physician_specialty: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Especialidad médica",
        examples=["Medicina General", "Pediatría", "Cardiología"],
    )

    physician_license: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Cédula profesional",
    )

    physician_university: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Universidad de egreso",
    )

    physician_specialty_license: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Cédula de especialidad",
    )

    model_config = ConfigDict(extra="allow")


class FooterConfig(BaseModel):
    """Configuration for prescription footer.

    Contains signature area and legal disclaimers.
    """

    include_signature_line: bool = Field(
        default=True,
        description="Incluir línea para firma",
    )

    signature_label: str = Field(
        default="Firma del Médico",
        max_length=100,
    )

    include_date_line: bool = Field(
        default=True,
        description="Incluir línea para fecha",
    )

    disclaimer_text: Optional[str] = Field(
        default="Esta receta es válida únicamente con firma y sello del médico.",
        max_length=500,
        description="Texto legal/disclaimer",
    )

    include_qr_code: bool = Field(
        default=False,
        description="Incluir código QR de verificación",
    )

    model_config = ConfigDict(extra="allow")


class PrescriptionTemplate(BaseModel):
    """Complete prescription template configuration.

    A template defines the layout and configuration for generating
    prescriptions. Can be customized per physician or institution.

    Attributes:
        id: Unique template identifier
        name: Template name for display
        description: Template description
        owner_id: Physician or institution ID that owns this template
        is_default: Whether this is the default template
        header: Header configuration (membrete)
        footer: Footer configuration
        fields: List of customizable fields
        medication_fields: Fields shown for each medication
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_active: Whether template is active
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="ID único del template",
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nombre del template",
        examples=["Receta Estándar", "Receta Pediátrica", "Receta Controlada"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descripción del template",
    )

    owner_id: Optional[str] = Field(
        default=None,
        description="ID del médico o institución propietario",
    )

    owner_type: str = Field(
        default="physician",
        description="Tipo de propietario: physician, institution, system",
    )

    is_default: bool = Field(
        default=False,
        description="Si es el template por defecto",
    )

    header: HeaderConfig = Field(
        default_factory=HeaderConfig,
        description="Configuración del encabezado",
    )

    footer: FooterConfig = Field(
        default_factory=FooterConfig,
        description="Configuración del pie de página",
    )

    fields: list[TemplateField] = Field(
        default_factory=list,
        description="Campos personalizables del template",
    )

    # Default medication fields that every template includes
    medication_fields: list[str] = Field(
        default_factory=lambda: [
            "name",
            "dosage",
            "dosage_form",
            "frequency",
            "duration_days",
            "route",
            "quantity",
            "instructions",
        ],
        description="Campos de medicamento visibles en este template",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de creación",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Fecha de última actualización",
    )

    is_active: bool = Field(
        default=True,
        description="Si el template está activo",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Receta Estándar",
                "description": "Template básico para consulta general",
                "owner_type": "physician",
                "is_default": True,
                "header": {
                    "institution_name": "Consultorio Médico",
                    "physician_name": "Dr. Juan Pérez",
                    "physician_specialty": "Medicina General",
                    "physician_license": "12345678",
                },
                "footer": {
                    "include_signature_line": True,
                    "disclaimer_text": "Esta receta es válida únicamente con firma y sello.",
                },
            }
        },
    )

    @field_validator("fields", mode="after")
    @classmethod
    def sort_fields_by_order(cls, v: list[TemplateField]) -> list[TemplateField]:
        """Sort fields by their order attribute."""
        return sorted(v, key=lambda f: f.order)

    def get_required_fields(self) -> list[TemplateField]:
        """Get all required fields."""
        return [f for f in self.fields if f.required and f.visible]

    def get_visible_fields(self) -> list[TemplateField]:
        """Get all visible fields sorted by order."""
        return [f for f in self.fields if f.visible]

    def validate_data(self, data: dict[str, Any]) -> list[str]:
        """Validate prescription data against template fields.

        Args:
            data: Dictionary of field values

        Returns:
            List of validation error messages
        """
        errors: list[str] = []

        for field in self.get_required_fields():
            value = data.get(field.key)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Campo requerido: {field.label}")
            elif field.min_length and isinstance(value, str) and len(value) < field.min_length:
                errors.append(f"{field.label}: mínimo {field.min_length} caracteres")
            elif field.max_length and isinstance(value, str) and len(value) > field.max_length:
                errors.append(f"{field.label}: máximo {field.max_length} caracteres")

        return errors


def get_default_template() -> PrescriptionTemplate:
    """Create the default prescription template.

    Returns a template with standard Mexican prescription fields.
    """
    return PrescriptionTemplate(
        id="default",
        name="Receta Estándar",
        description="Template estándar para consulta médica general",
        owner_type="system",
        is_default=True,
        header=HeaderConfig(),
        footer=FooterConfig(),
        fields=[
            TemplateField(
                key="patient_name",
                label="Nombre del Paciente",
                field_type=FieldType.TEXT,
                required=True,
                order=1,
            ),
            TemplateField(
                key="patient_age",
                label="Edad",
                field_type=FieldType.TEXT,
                required=True,
                placeholder="Ej: 35 años",
                order=2,
            ),
            TemplateField(
                key="patient_weight",
                label="Peso (kg)",
                field_type=FieldType.NUMBER,
                required=False,
                order=3,
            ),
            TemplateField(
                key="diagnosis",
                label="Diagnóstico",
                field_type=FieldType.TEXTAREA,
                required=True,
                placeholder="Diagnóstico principal",
                order=4,
            ),
            TemplateField(
                key="medications",
                label="Medicamentos",
                field_type=FieldType.MEDICATION,
                required=True,
                order=5,
                help_text="Agregue los medicamentos prescritos",
            ),
            TemplateField(
                key="general_instructions",
                label="Indicaciones Generales",
                field_type=FieldType.TEXTAREA,
                required=False,
                placeholder="Instrucciones adicionales para el paciente",
                order=6,
            ),
            TemplateField(
                key="next_appointment",
                label="Próxima Cita",
                field_type=FieldType.TEXT,
                required=False,
                placeholder="Ej: En 2 semanas",
                order=7,
            ),
        ],
    )
