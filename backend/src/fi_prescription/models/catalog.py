"""Medication Catalog model for drug database.

Defines the structure for medication entries in the catalog,
including generic names, commercial brands, presentations,
and standard dosing information.

Based on Mexican pharmaceutical standards (COFEPRIS/Cuadro Básico).

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-004
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fi_prescription.models.medication import MedicationRoute
from pydantic import BaseModel, ConfigDict, Field


class DrugCategory(str, Enum):
    """Therapeutic categories for medications."""

    ANALGESIC = "analgesic"  # Analgésicos
    ANTIBIOTIC = "antibiotic"  # Antibióticos
    ANTIVIRAL = "antiviral"  # Antivirales
    ANTIFUNGAL = "antifungal"  # Antimicóticos
    ANTIINFLAMMATORY = "antiinflammatory"  # Antiinflamatorios
    ANTIHYPERTENSIVE = "antihypertensive"  # Antihipertensivos
    ANTIDIABETIC = "antidiabetic"  # Antidiabéticos
    ANTIHISTAMINE = "antihistamine"  # Antihistamínicos
    ANTACID = "antacid"  # Antiácidos/IBP
    BRONCHODILATOR = "bronchodilator"  # Broncodilatadores
    CORTICOSTEROID = "corticosteroid"  # Corticosteroides
    ANTIDEPRESSANT = "antidepressant"  # Antidepresivos
    ANXIOLYTIC = "anxiolytic"  # Ansiolíticos
    ANTIPSYCHOTIC = "antipsychotic"  # Antipsicóticos
    ANTICOAGULANT = "anticoagulant"  # Anticoagulantes
    ANTICONVULSANT = "anticonvulsant"  # Anticonvulsivos
    DIURETIC = "diuretic"  # Diuréticos
    VITAMIN = "vitamin"  # Vitaminas/Suplementos
    HORMONE = "hormone"  # Hormonas
    MUSCLE_RELAXANT = "muscle_relaxant"  # Relajantes musculares
    GASTROINTESTINAL = "gastrointestinal"  # Gastrointestinales
    DERMATOLOGIC = "dermatologic"  # Dermatológicos
    OPHTHALMIC = "ophthalmic"  # Oftálmicos
    OTIC = "otic"  # Óticos
    OTHER = "other"  # Otros


class ControlledSubstanceLevel(str, Enum):
    """Controlled substance classification (Mexico - Ley General de Salud)."""

    NONE = "none"  # Sin control
    FRACTION_I = "fraction_i"  # Fracción I - No uso médico
    FRACTION_II = "fraction_ii"  # Fracción II - Receta especial
    FRACTION_III = "fraction_iii"  # Fracción III - Receta retenida
    FRACTION_IV = "fraction_iv"  # Fracción IV - Receta médica
    FRACTION_V = "fraction_v"  # Fracción V - OTC con restricciones
    FRACTION_VI = "fraction_vi"  # Fracción VI - OTC


class Presentation(BaseModel):
    """A specific presentation/formulation of a medication."""

    form: str = Field(
        ...,
        description="Forma farmacéutica",
        examples=["tableta", "cápsula", "jarabe", "suspensión", "inyectable"],
    )

    strength: str = Field(
        ...,
        description="Concentración/potencia",
        examples=["500mg", "250mg/5ml", "10mg/ml"],
    )

    unit: str = Field(
        default="unidad",
        description="Unidad de presentación",
        examples=["tableta", "cápsula", "ml", "ampolleta"],
    )

    package_size: str | None = Field(
        default=None,
        description="Tamaño del empaque",
        examples=["20 tabletas", "120ml", "10 ampolletas"],
    )

    route: MedicationRoute = Field(
        default=MedicationRoute.ORAL,
        description="Vía de administración principal",
    )

    model_config = ConfigDict(extra="forbid")


class StandardDosing(BaseModel):
    """Standard dosing information for a medication."""

    adult_dose: str = Field(
        ...,
        description="Dosis estándar para adultos",
        examples=["500mg cada 8 horas", "1 tableta cada 12 horas"],
    )

    pediatric_dose: str | None = Field(
        default=None,
        description="Dosis pediátrica (si aplica)",
        examples=["10-15mg/kg/día dividido en 3 dosis"],
    )

    max_daily_dose: str | None = Field(
        default=None,
        description="Dosis máxima diaria",
        examples=["4g/día", "8 tabletas/día"],
    )

    duration_typical: str | None = Field(
        default=None,
        description="Duración típica del tratamiento",
        examples=["7-10 días", "Uso crónico", "Dosis única"],
    )

    notes: str | None = Field(
        default=None,
        description="Notas adicionales de dosificación",
    )

    model_config = ConfigDict(extra="forbid")


class MedicationCatalogEntry(BaseModel):
    """Entry in the medication catalog.

    Represents a single medication with all its information
    for use in prescription autocomplete and validation.

    Attributes:
        id: Unique identifier
        generic_name: Nombre genérico (denominación común internacional)
        active_ingredient: Principio activo
        commercial_names: Lista de nombres comerciales comunes
        category: Categoría terapéutica
        presentations: Presentaciones disponibles
        standard_dosing: Información de dosificación estándar
        contraindications: Contraindicaciones principales
        interactions: Interacciones medicamentosas importantes
        warnings: Advertencias especiales
        controlled_level: Nivel de control (sustancia controlada)
        requires_prescription: Si requiere receta médica
        cofepris_key: Clave COFEPRIS (si aplica)
        is_essential: Si está en cuadro básico de medicamentos
    """

    id: str = Field(
        ...,
        description="Identificador único del medicamento",
    )

    generic_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre genérico (DCI)",
        examples=["Paracetamol", "Amoxicilina", "Metformina"],
    )

    active_ingredient: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Principio activo",
    )

    commercial_names: list[str] = Field(
        default_factory=list,
        description="Nombres comerciales comunes en México",
        examples=[["Tempra", "Tylenol"], ["Amoxil", "Trimox"]],
    )

    category: DrugCategory = Field(
        default=DrugCategory.OTHER,
        description="Categoría terapéutica",
    )

    presentations: list[Presentation] = Field(
        default_factory=list,
        description="Presentaciones disponibles",
    )

    standard_dosing: StandardDosing | None = Field(
        default=None,
        description="Dosificación estándar",
    )

    contraindications: list[str] = Field(
        default_factory=list,
        description="Contraindicaciones principales",
    )

    interactions: list[str] = Field(
        default_factory=list,
        description="Interacciones medicamentosas importantes",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Advertencias especiales",
    )

    controlled_level: ControlledSubstanceLevel = Field(
        default=ControlledSubstanceLevel.NONE,
        description="Clasificación como sustancia controlada",
    )

    requires_prescription: bool = Field(
        default=True,
        description="Requiere receta médica",
    )

    cofepris_key: str | None = Field(
        default=None,
        description="Clave de registro sanitario COFEPRIS",
    )

    is_essential: bool = Field(
        default=False,
        description="Incluido en cuadro básico de medicamentos",
    )

    is_active: bool = Field(
        default=True,
        description="Si el medicamento está activo en el catálogo",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "paracetamol",
                "generic_name": "Paracetamol",
                "active_ingredient": "Paracetamol (Acetaminofén)",
                "commercial_names": ["Tempra", "Tylenol", "Mejoral"],
                "category": "analgesic",
                "presentations": [
                    {"form": "tableta", "strength": "500mg", "route": "oral"},
                    {"form": "jarabe", "strength": "120mg/5ml", "route": "oral"},
                ],
                "standard_dosing": {
                    "adult_dose": "500-1000mg cada 6-8 horas",
                    "pediatric_dose": "10-15mg/kg cada 6 horas",
                    "max_daily_dose": "4g/día",
                },
                "contraindications": ["Hipersensibilidad al paracetamol"],
                "warnings": ["Hepatotoxicidad en dosis altas", "Precaución en alcoholismo"],
                "controlled_level": "none",
                "requires_prescription": False,
                "is_essential": True,
            }
        },
    )

    def matches_search(self, query: str) -> bool:
        """Check if this medication matches a search query.

        Args:
            query: Search string (case-insensitive)

        Returns:
            True if matches generic name, active ingredient, or commercial names
        """
        query_lower = query.lower()

        # Check generic name
        if query_lower in self.generic_name.lower():
            return True

        # Check active ingredient
        if query_lower in self.active_ingredient.lower():
            return True

        # Check commercial names
        return any(query_lower in name.lower() for name in self.commercial_names)

    def get_search_score(self, query: str) -> int:
        """Calculate relevance score for search ranking.

        Args:
            query: Search string

        Returns:
            Score (higher = more relevant)
        """
        query_lower = query.lower()
        score = 0

        # Exact match on generic name
        if query_lower == self.generic_name.lower():
            score += 100

        # Starts with query
        if self.generic_name.lower().startswith(query_lower):
            score += 50

        # Contains query
        if query_lower in self.generic_name.lower():
            score += 25

        # Commercial name matches
        for name in self.commercial_names:
            if query_lower == name.lower():
                score += 80
            elif name.lower().startswith(query_lower):
                score += 40
            elif query_lower in name.lower():
                score += 20

        # Boost essential medications
        if self.is_essential:
            score += 10

        return score
