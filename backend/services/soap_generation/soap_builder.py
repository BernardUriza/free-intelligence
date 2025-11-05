"""SOAP model builder from extracted data.

This module constructs Pydantic SOAP models from extracted JSON data,
handling type conversions and validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from backend.logger import get_logger
from backend.providers.fi_consult_models import (
    Analisis,
    Antecedentes,
    DiagnosticoDiferencial,
    DiagnosticoPrincipal,
    ExploracionFisica,
    Gravedad,
    Objetivo,
    Plan,
    Pronostico,
    SignosVitales,
    SOAPMetadata,
    SOAPNote,
    Subjetivo,
    UrgenciaTriaje,
)

__all__ = ["SOAPBuilder", "SOAPBuildError"]

logger = get_logger(__name__)


class SOAPBuildError(Exception):
    """Raised when SOAP model cannot be built."""

    pass


class SOAPBuilder:
    """Builds SOAP model instances from extracted JSON data."""

    @staticmethod
    def build(job_id: str, soap_data: dict[str, Any]) -> tuple[Subjetivo, Objetivo, Analisis, Plan]:
        """Build SOAP sections from extracted data.

        Args:
            job_id: Diarization job ID
            soap_data: Extracted SOAP data dictionary

        Returns:
            Tuple of (Subjetivo, Objetivo, Analisis, Plan) models

        Raises:
            SOAPBuildError: If models cannot be constructed
        """
        try:
            subjetivo = SOAPBuilder._build_subjetivo(soap_data)
            objetivo = SOAPBuilder._build_objetivo(soap_data)
            analisis = SOAPBuilder._build_analisis(soap_data)
            plan = SOAPBuilder._build_plan(soap_data)

            return subjetivo, objetivo, analisis, plan

        except ValidationError as e:
            logger.error("SOAP_VALIDATION_FAILED", job_id=job_id, errors=str(e))
            raise SOAPBuildError(f"Failed to build SOAP models: {str(e)}") from e
        except Exception as e:
            logger.error("SOAP_BUILD_FAILED", job_id=job_id, error=str(e))
            raise SOAPBuildError(f"Unexpected error building SOAP: {str(e)}") from e

    @staticmethod
    def build_note(
        job_id: str,
        subjetivo: Subjetivo,
        objetivo: Objetivo,
        analisis: Analisis,
        plan: Plan,
        completeness: float,
    ) -> SOAPNote:
        """Build complete SOAPNote model.

        Args:
            job_id: Consultation ID
            subjetivo: Subjective section
            objetivo: Objective section
            analisis: Analysis section
            plan: Plan section
            completeness: Completeness score (0-100)

        Returns:
            SOAPNote model instance

        Raises:
            SOAPBuildError: If note cannot be constructed
        """
        try:
            metadata = SOAPMetadata(
                medico="Sistema Automatizado",
                especialidad="General",
                fecha=datetime.now(),
                duracion_consulta=0,
                consentimiento_informado=True,
            )

            return SOAPNote(
                consultation_id=job_id,
                subjetivo=subjetivo,
                objetivo=objetivo,
                analisis=analisis,
                plan=plan,
                metadata=metadata,
                completeness=completeness,
            )

        except ValidationError as e:
            raise SOAPBuildError(f"Failed to build SOAPNote: {str(e)}") from e

    @staticmethod
    def _build_subjetivo(soap_data: dict[str, Any]) -> Subjetivo:
        """Build Subjetivo section."""
        subjetivo_data = soap_data.get("subjetivo", {})

        # Parse antecedentes
        antecedentes_raw = subjetivo_data.get("antecedentes", {})
        if isinstance(antecedentes_raw, str):
            antecedentes_data = {"personales": [antecedentes_raw] if antecedentes_raw else []}
        else:
            antecedentes_data = antecedentes_raw or {}

        antecedentes = Antecedentes(
            personales=antecedentes_data.get("personales", []),
            familiares=antecedentes_data.get("familiares", []),
            medicamentos=antecedentes_data.get("medicamentos", []),
            alergias=antecedentes_data.get("alergias", []),
            quirurgicos=antecedentes_data.get("quirurgicos", []),
        )

        return Subjetivo(
            motivo_consulta=subjetivo_data.get("motivo_consulta", ""),
            historia_actual=subjetivo_data.get("historia_actual", ""),
            antecedentes=antecedentes,
        )

    @staticmethod
    def _build_objetivo(soap_data: dict[str, Any]) -> Objetivo:
        """Build Objetivo section."""
        objetivo_data = soap_data.get("objetivo", {})

        # Parse signos vitales
        signos_vitales_raw = objetivo_data.get("signos_vitales", {})
        if isinstance(signos_vitales_raw, str):
            signos_vitales_data = {"presion_arterial": signos_vitales_raw or None}
        else:
            signos_vitales_data = signos_vitales_raw or {}

        signos_vitales = SignosVitales(
            presion_arterial=signos_vitales_data.get("presion_arterial"),
            frecuencia_cardiaca=SOAPBuilder._to_int(signos_vitales_data.get("frecuencia_cardiaca")),
            frecuencia_respiratoria=SOAPBuilder._to_int(
                signos_vitales_data.get("frecuencia_respiratoria")
            ),
            temperatura=SOAPBuilder._to_float(signos_vitales_data.get("temperatura")),
            saturacion_oxigeno=SOAPBuilder._to_float(signos_vitales_data.get("saturacion_oxigeno")),
            peso=SOAPBuilder._to_float(signos_vitales_data.get("peso")),
        )

        # Parse exploracion fisica
        examen_fisico_raw = objetivo_data.get("examen_fisico", "")
        exploracion_fisica = ExploracionFisica(
            aspecto=examen_fisico_raw or "Examen físico realizado",
            cabeza_cuello=objetivo_data.get("cabeza_cuello"),
            torax=objetivo_data.get("torax"),
            cardiovascular=objetivo_data.get("cardiovascular"),
            pulmonar=objetivo_data.get("pulmonar"),
            abdomen=objetivo_data.get("abdomen"),
            extremidades=objetivo_data.get("extremidades"),
            neurologico=objetivo_data.get("neurologico"),
            piel=objetivo_data.get("piel"),
        )

        return Objetivo(
            signos_vitales=signos_vitales,
            exploracion_fisica=exploracion_fisica,
        )

    @staticmethod
    def _build_analisis(soap_data: dict[str, Any]) -> Analisis:
        """Build Analisis section."""
        analisis_data = soap_data.get("analisis", {})

        # Build diagnostico principal
        diagnostico_principal_raw = analisis_data.get("diagnostico_principal", "")
        if isinstance(diagnostico_principal_raw, str):
            diagnostico_principal = DiagnosticoPrincipal(
                condicion=diagnostico_principal_raw or "Diagnóstico pendiente",
                cie10="R69.9",
                evidencia=[],
                probabilidad=0.5,
                confianza=0.5,
            )
        else:
            diagnostico_principal = diagnostico_principal_raw

        # Build diagnosticos diferenciales
        diferenciales_raw = analisis_data.get("diagnosticos_diferenciales", [])
        diagnosticos_diferenciales = SOAPBuilder._build_diagnosticos_diferenciales(
            diferenciales_raw
        )

        # Build pronostico
        pronostico_raw = analisis_data.get("pronostico", {})
        if isinstance(pronostico_raw, dict):
            pronostico = Pronostico(
                inmediato=pronostico_raw.get("inmediato", "Favorable"),
                corto=pronostico_raw.get("corto", "Favorable"),
                largo=pronostico_raw.get("largo", "Favorable"),
            )
        else:
            pronostico = Pronostico(
                inmediato="Favorable",
                corto="Favorable",
                largo="Favorable",
            )

        return Analisis(
            diagnostico_principal=diagnostico_principal,
            diagnosticos_diferenciales=diagnosticos_diferenciales,
            factores_riesgo=analisis_data.get("factores_riesgo", []),
            senos_peligro=analisis_data.get("senos_peligro", []),
            pronostico=pronostico,
            razonamiento_clinico=analisis_data.get("razonamiento_clinico"),
        )

    @staticmethod
    def _build_diagnosticos_diferenciales(
        diferenciales_raw: Any,
    ) -> list[DiagnosticoDiferencial]:
        """Build list of differential diagnoses."""
        diagnosticos_diferenciales = []

        if not isinstance(diferenciales_raw, list):
            return diagnosticos_diferenciales

        for dx in diferenciales_raw:
            if isinstance(dx, str):
                diagnosticos_diferenciales.append(
                    DiagnosticoDiferencial(
                        condicion=dx,
                        cie10="R69.9",
                        probabilidad=0.3,
                        gravedad=Gravedad.MODERADA,
                        urgencia=UrgenciaTriaje.NO_URGENTE,
                        defensive_score=0.4,
                    )
                )
            elif isinstance(dx, dict):
                diagnosticos_diferenciales.append(
                    DiagnosticoDiferencial(
                        condicion=dx.get("condicion", ""),
                        cie10=dx.get("cie10", "R69.9"),
                        probabilidad=float(dx.get("probabilidad", 0.3)),
                        gravedad=Gravedad(dx.get("gravedad", "moderada")),
                        urgencia=UrgenciaTriaje(dx.get("urgencia", "no_urgente")),
                        defensive_score=float(dx.get("defensive_score", 0.4)),
                    )
                )

        return diagnosticos_diferenciales

    @staticmethod
    def _build_plan(soap_data: dict[str, Any]) -> Plan:
        """Build Plan section."""
        from backend.providers.fi_consult_models import Seguimiento

        plan_data = soap_data.get("plan", {})

        # Parse seguimiento
        seguimiento_raw = plan_data.get("seguimiento", {})
        if isinstance(seguimiento_raw, str):
            seguimiento = Seguimiento(
                proxima_cita=seguimiento_raw or "A convenir",
                vigilar=[],
                criterios_emergencia=[],
                educacion_paciente=[],
            )
        else:
            seguimiento = Seguimiento(
                proxima_cita=seguimiento_raw.get("proxima_cita", "A convenir"),
                vigilar=seguimiento_raw.get("vigilar", []),
                criterios_emergencia=seguimiento_raw.get("criterios_emergencia", []),
                educacion_paciente=seguimiento_raw.get("educacion_paciente", []),
            )

        return Plan(
            tratamiento_farmacologico=[],
            tratamiento_no_farmacologico=[],
            estudios_adicionales=[],
            interconsultas=[],
            seguimiento=seguimiento,
        )

    @staticmethod
    def _to_int(val: Any) -> int | None:
        """Convert value to int or None."""
        if val is None or val == "":
            return None
        try:
            return int(val) if isinstance(val, str) else val
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_float(val: Any) -> float | None:
        """Convert value to float or None."""
        if val is None or val == "":
            return None
        try:
            return float(val) if isinstance(val, str) else val
        except (ValueError, TypeError):
            return None
