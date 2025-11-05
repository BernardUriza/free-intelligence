"""Default SOAP structures for fallback scenarios.

This module provides default empty/fallback SOAP structures
used when LLM extraction fails or returns invalid data.
"""

from __future__ import annotations

from typing import Any

__all__ = ["get_default_soap_structure"]


def get_default_soap_structure() -> dict[str, Any]:
    """Return default empty SOAP structure.

    Used as fallback when Ollama extraction fails or returns invalid JSON.
    Ensures graceful degradation with empty but valid structure.

    Returns:
        Dictionary with SOAP structure (subjetivo, objetivo, analisis, plan)
    """
    return {
        "subjetivo": {
            "motivo_consulta": "",
            "historia_actual": "",
            "antecedentes": "",
        },
        "objetivo": {
            "signos_vitales": "",
            "examen_fisico": "",
        },
        "analisis": {
            "diagnosticos_diferenciales": [],
            "diagnostico_principal": "",
        },
        "plan": {
            "tratamiento": "",
            "seguimiento": "",
            "estudios": [],
        },
    }
