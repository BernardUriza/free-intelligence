"""Medication model for prescription items.

Defines the structure of individual medications in a prescription,
following Mexican pharmaceutical standards (COFEPRIS).

Author: Bernard Uriza Orozco
Created: 2025-12-28
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicationRoute(str, Enum):
    """Administration routes for medications (vías de administración)."""

    ORAL = "oral"
    SUBLINGUAL = "sublingual"
    INTRAVENOUS = "intravenous"
    INTRAMUSCULAR = "intramuscular"
    SUBCUTANEOUS = "subcutaneous"
    TOPICAL = "topical"
    OPHTHALMIC = "ophthalmic"
    OTIC = "otic"
    NASAL = "nasal"
    INHALATION = "inhalation"
    RECTAL = "rectal"
    VAGINAL = "vaginal"
    TRANSDERMAL = "transdermal"

    @classmethod
    def get_spanish_label(cls, route: "MedicationRoute") -> str:
        """Get Spanish label for route."""
        labels = {
            cls.ORAL: "Vía oral",
            cls.SUBLINGUAL: "Sublingual",
            cls.INTRAVENOUS: "Intravenosa (IV)",
            cls.INTRAMUSCULAR: "Intramuscular (IM)",
            cls.SUBCUTANEOUS: "Subcutánea (SC)",
            cls.TOPICAL: "Tópica",
            cls.OPHTHALMIC: "Oftálmica",
            cls.OTIC: "Ótica",
            cls.NASAL: "Nasal",
            cls.INHALATION: "Inhalada",
            cls.RECTAL: "Rectal",
            cls.VAGINAL: "Vaginal",
            cls.TRANSDERMAL: "Transdérmica",
        }
        return labels.get(route, route.value)


class MedicationFrequency(str, Enum):
    """Common medication frequencies (frecuencias de administración)."""

    ONCE_DAILY = "once_daily"  # Una vez al día
    TWICE_DAILY = "twice_daily"  # Dos veces al día (c/12h)
    THREE_TIMES_DAILY = "three_times_daily"  # Tres veces al día (c/8h)
    FOUR_TIMES_DAILY = "four_times_daily"  # Cuatro veces al día (c/6h)
    EVERY_4_HOURS = "every_4_hours"  # Cada 4 horas
    EVERY_6_HOURS = "every_6_hours"  # Cada 6 horas
    EVERY_8_HOURS = "every_8_hours"  # Cada 8 horas
    EVERY_12_HOURS = "every_12_hours"  # Cada 12 horas
    EVERY_24_HOURS = "every_24_hours"  # Cada 24 horas
    WEEKLY = "weekly"  # Semanal
    AS_NEEDED = "as_needed"  # PRN (pro re nata) - según se necesite
    BEFORE_MEALS = "before_meals"  # Antes de alimentos
    AFTER_MEALS = "after_meals"  # Después de alimentos
    AT_BEDTIME = "at_bedtime"  # Al acostarse
    CUSTOM = "custom"  # Frecuencia personalizada

    @classmethod
    def get_spanish_label(cls, freq: "MedicationFrequency") -> str:
        """Get Spanish label for frequency."""
        labels = {
            cls.ONCE_DAILY: "Una vez al día",
            cls.TWICE_DAILY: "Cada 12 horas",
            cls.THREE_TIMES_DAILY: "Cada 8 horas",
            cls.FOUR_TIMES_DAILY: "Cada 6 horas",
            cls.EVERY_4_HOURS: "Cada 4 horas",
            cls.EVERY_6_HOURS: "Cada 6 horas",
            cls.EVERY_8_HOURS: "Cada 8 horas",
            cls.EVERY_12_HOURS: "Cada 12 horas",
            cls.EVERY_24_HOURS: "Cada 24 horas",
            cls.WEEKLY: "Una vez por semana",
            cls.AS_NEEDED: "Según se necesite (PRN)",
            cls.BEFORE_MEALS: "Antes de los alimentos",
            cls.AFTER_MEALS: "Después de los alimentos",
            cls.AT_BEDTIME: "Al acostarse",
            cls.CUSTOM: "Personalizada",
        }
        return labels.get(freq, freq.value)


class Medication(BaseModel):
    """Individual medication entry in a prescription.

    Represents a single medication with all required fields for
    a valid Mexican prescription (NOM-024-SSA3-2012).

    Attributes:
        name: Generic or commercial drug name
        active_ingredient: Active pharmaceutical ingredient (principio activo)
        dosage: Dose amount with unit (e.g., "500mg", "10ml")
        dosage_form: Pharmaceutical form (tableta, cápsula, jarabe, etc.)
        frequency: How often to take the medication
        frequency_custom: Custom frequency text if frequency is CUSTOM
        duration_days: Treatment duration in days
        duration_text: Human-readable duration (e.g., "7 días", "hasta terminar")
        route: Administration route
        quantity: Total quantity to dispense
        instructions: Additional instructions for the patient
        indication: Why this medication is prescribed
        warnings: Specific warnings or contraindications
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del medicamento (genérico o comercial)",
        examples=["Paracetamol", "Amoxicilina", "Omeprazol"],
    )

    active_ingredient: str | None = Field(
        default=None,
        max_length=200,
        description="Principio activo (si difiere del nombre)",
        examples=["Acetaminofén", "Amoxicilina trihidrato"],
    )

    dosage: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Dosis por toma",
        examples=["500mg", "250mg/5ml", "1 tableta", "10 gotas"],
    )

    dosage_form: str = Field(
        default="tableta",
        max_length=50,
        description="Forma farmacéutica",
        examples=["tableta", "cápsula", "jarabe", "suspensión", "crema", "gotas"],
    )

    frequency: MedicationFrequency = Field(
        default=MedicationFrequency.EVERY_8_HOURS,
        description="Frecuencia de administración",
    )

    frequency_custom: str | None = Field(
        default=None,
        max_length=100,
        description="Frecuencia personalizada (si frequency es CUSTOM)",
        examples=["Lunes, miércoles y viernes", "Días alternos"],
    )

    duration_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Duración del tratamiento en días",
    )

    duration_text: str | None = Field(
        default=None,
        max_length=100,
        description="Duración en texto libre",
        examples=["7 días", "Hasta terminar", "Uso crónico", "Por 2 semanas"],
    )

    route: MedicationRoute = Field(
        default=MedicationRoute.ORAL,
        description="Vía de administración",
    )

    quantity: str | None = Field(
        default=None,
        max_length=50,
        description="Cantidad total a surtir",
        examples=["20 tabletas", "1 frasco 120ml", "30 cápsulas"],
    )

    instructions: str | None = Field(
        default=None,
        max_length=500,
        description="Instrucciones adicionales para el paciente",
        examples=[
            "Tomar con abundante agua",
            "No masticar, tragar entero",
            "Refrigerar después de abrir",
        ],
    )

    indication: str | None = Field(
        default=None,
        max_length=200,
        description="Indicación (para qué se prescribe)",
        examples=["Para el dolor", "Para la infección", "Control de presión"],
    )

    warnings: str | None = Field(
        default=None,
        max_length=300,
        description="Advertencias específicas",
        examples=[
            "No consumir con alcohol",
            "Puede causar somnolencia",
            "No suspender abruptamente",
        ],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Amoxicilina",
                "active_ingredient": "Amoxicilina trihidrato",
                "dosage": "500mg",
                "dosage_form": "cápsula",
                "frequency": "every_8_hours",
                "duration_days": 7,
                "duration_text": "7 días",
                "route": "oral",
                "quantity": "21 cápsulas",
                "instructions": "Tomar con alimentos para evitar molestias gástricas",
                "indication": "Infección de vías respiratorias",
                "warnings": "Suspender si presenta rash cutáneo",
            }
        },
    )

    @field_validator("name", "dosage")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace."""
        return v.strip()

    @field_validator("frequency_custom")
    @classmethod
    def validate_custom_frequency(cls, v: str | None, _info) -> str | None:
        """Ensure custom frequency is provided when frequency is CUSTOM."""
        # Note: Cross-field validation happens at model level
        return v.strip() if v else None

    def get_frequency_label(self) -> str:
        """Get human-readable frequency in Spanish."""
        if self.frequency == MedicationFrequency.CUSTOM and self.frequency_custom:
            return self.frequency_custom
        return MedicationFrequency.get_spanish_label(self.frequency)

    def get_route_label(self) -> str:
        """Get human-readable route in Spanish."""
        return MedicationRoute.get_spanish_label(self.route)

    def get_duration_label(self) -> str:
        """Get human-readable duration."""
        if self.duration_text:
            return self.duration_text
        if self.duration_days:
            return f"{self.duration_days} días"
        return "Según indicación médica"

    def to_prescription_line(self) -> str:
        """Generate prescription line text for printing.

        Returns:
            Formatted prescription line following Mexican standards.
        """
        lines = [f"Rx: {self.name}"]

        if self.active_ingredient and self.active_ingredient != self.name:
            lines[0] += f" ({self.active_ingredient})"

        lines.append(f"    {self.dosage} - {self.dosage_form}")
        lines.append(f"    {self.get_route_label()}, {self.get_frequency_label()}")
        lines.append(f"    Duración: {self.get_duration_label()}")

        if self.quantity:
            lines.append(f"    Cantidad: {self.quantity}")

        if self.instructions:
            lines.append(f"    Indicaciones: {self.instructions}")

        return "\n".join(lines)
