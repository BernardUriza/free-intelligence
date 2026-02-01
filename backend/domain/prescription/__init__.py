# fi_prescription - Medical Prescription Template Engine
"""
Template Engine para recetas médicas.

Módulo que maneja:
- Templates configurables por médico/institución
- Medicamentos con dosis, frecuencia, duración, vía
- Generación de recetas desde SOAP notes
- Validación de campos requeridos por normativa mexicana

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-002
"""

from backend.domain.prescription.models.medication import (
    Medication,
    MedicationFrequency,
    MedicationRoute,
)
from backend.domain.prescription.models.prescription import Prescription, PrescriptionStatus
from backend.domain.prescription.models.template import PrescriptionTemplate, TemplateField

__all__ = [
    "Medication",
    "MedicationRoute",
    "MedicationFrequency",
    "Prescription",
    "PrescriptionStatus",
    "PrescriptionTemplate",
    "TemplateField",
]
