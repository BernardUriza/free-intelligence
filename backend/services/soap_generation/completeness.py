"""SOAP completeness scoring logic.

This module calculates completeness scores for SOAP notes
based on presence of key clinical sections.
"""

from __future__ import annotations

from backend.providers.models import Analisis, Objetivo, Plan, Subjetivo

__all__ = ["CompletenessCalculator"]

# Scoring weights for each SOAP section
SCORE_CONFIG = {
    "motivo_consulta": 15,
    "historia_actual": 10,
    "signos_vitales": 15,
    "exploracion_fisica": 10,
    "diagnostico_principal": 20,
    "diagnosticos_diferenciales": 10,
    "tratamiento_farmacologico": 15,
}


class CompletenessCalculator:
    """Calculates SOAP note completeness scores.

    Evaluates presence of key clinical sections and assigns
    weighted scores (0-100).
    """

    @staticmethod
    def calculate(
        subjetivo: Subjetivo,
        objetivo: Objetivo,
        analisis: Analisis,
        plan: Plan,
    ) -> float:
        """Calculate SOAP completeness score (0-100).

        Args:
            subjetivo: Subjective section
            objetivo: Objective section
            analisis: Analysis section
            plan: Plan section

        Returns:
            Completeness score (0-100)
        """
        score = 0.0

        # Subjective section
        if subjetivo.motivo_consulta:
            score += SCORE_CONFIG["motivo_consulta"]
        if subjetivo.historia_actual:
            score += SCORE_CONFIG["historia_actual"]

        # Objective section
        if objetivo.signos_vitales:
            score += SCORE_CONFIG["signos_vitales"]
        if objetivo.exploracion_fisica:
            score += SCORE_CONFIG["exploracion_fisica"]

        # Analysis section
        if analisis.diagnostico_principal:
            score += SCORE_CONFIG["diagnostico_principal"]
        if analisis.diagnosticos_diferenciales:
            score += SCORE_CONFIG["diagnosticos_diferenciales"]

        # Plan section
        if plan.tratamiento_farmacologico:
            score += SCORE_CONFIG["tratamiento_farmacologico"]

        # Cap at 100
        return min(score, 100.0)
