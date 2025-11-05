"""
SOAP Generation Service - MVP Level 1

Generates SOAP notes from diarization transcriptions using Ollama LLM.
Reads transcription from HDF5 diarization storage and structures it into SOAP format.

Card: FI-CONSULTATION-FEAT-001 (ConversationCapture - Level 1: MVP)

File: backend/services/soap_generation_service.py
Created: 2025-11-05
"""

from __future__ import annotations

import json
from typing import Optional

import h5py
from pydantic import ValidationError

from backend.fi_consult_models import (
    Analisis,
    DiagnosticoDiferencial,
    DiagnosticoPrincipal,
    EstudioUrgencia,
    ExploracionFisica,
    Gravedad,
    Interconsulta,
    Objetivo,
    Plan,
    Pronostico,
    Seguimiento,
    SOAPMetadata,
    SOAPNote,
    Subjetivo,
    TratamientoFarmacologico,
    UrgenciaTriaje,
)
from backend.logger import get_logger

logger = get_logger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # Use mistral or llama2


class SOAPGenerationService:
    """MVP Service to generate SOAP notes from diarization transcriptions."""

    def __init__(self, h5_path: str = "storage/diarization.h5"):
        """Initialize SOAP generation service.

        Args:
            h5_path: Path to diarization HDF5 file
        """
        self.h5_path = h5_path
        logger.info("SOAPGenerationService initialized", h5_path=h5_path)

    def generate_soap_for_job(self, job_id: str) -> SOAPNote:
        """Generate SOAP note from diarization job.

        Args:
            job_id: Diarization job ID

        Returns:
            SOAPNote with structured medical data

        Raises:
            ValueError: If job not found or transcription empty
        """
        try:
            # Step 1: Read transcription from HDF5
            transcription = self._read_transcription_from_h5(job_id)
            if not transcription:
                raise ValueError(f"No transcription found for job {job_id}")

            logger.info(
                "SOAP_GENERATION_START",
                job_id=job_id,
                transcription_length=len(transcription),
            )

            # Step 2: Call Ollama to extract SOAP sections
            soap_data = self._extract_soap_with_ollama(transcription)

            # Step 3: Create SOAPNote model
            soap_note = self._create_soap_note(job_id, soap_data)

            logger.info(
                "SOAP_GENERATION_COMPLETED",
                job_id=job_id,
                completeness=soap_note.completeness,
            )

            return soap_note

        except Exception as e:
            logger.error(
                "SOAP_GENERATION_FAILED", job_id=job_id, error=str(e)
            )  # type: ignore[call-arg]
            raise

    def _read_transcription_from_h5(self, job_id: str) -> str:
        """Read full transcription from HDF5 chunks.

        Args:
            job_id: Diarization job ID

        Returns:
            Concatenated transcription text
        """
        try:
            with h5py.File(self.h5_path, "r") as f:
                if f"diarization/{job_id}/chunks" not in f:
                    raise ValueError(f"No chunks found for job {job_id}")

                chunks_dataset = f[f"diarization/{job_id}/chunks"]
                texts = []

                # Read all chunks in order
                for i in range(len(chunks_dataset)):
                    row = chunks_dataset[i]
                    text = row["text"]
                    if isinstance(text, bytes):
                        text = text.decode("utf-8")
                    if text.strip():
                        texts.append(text)

                transcription = " ".join(texts)
                logger.info(
                    "TRANSCRIPTION_READ",
                    job_id=job_id,
                    chunks_count=len(chunks_dataset),
                    transcription_length=len(transcription),
                )

                return transcription

        except Exception as e:
            logger.error(
                "TRANSCRIPTION_READ_FAILED", job_id=job_id, error=str(e)
            )  # type: ignore[call-arg]
            raise

    def _extract_soap_with_ollama(self, transcription: str) -> dict:
        """Extract SOAP sections using Ollama LLM (language-agnostic).

        Accepts medical consultation transcriptions in ANY language.
        Extracts SOAP data without translating medical content.
        Returns standardized JSON with English field names (medical standard).

        Args:
            transcription: Full medical consultation transcription (any language)

        Returns:
            Dictionary with SOAP sections in English field names
        """
        try:
            import requests

            # Language-agnostic system prompt (accepts any input language)
            system_prompt = """You are a medical analyst. Analyze the medical consultation transcription provided.
Extract SOAP (Subjective-Objective-Assessment-Plan) data in a structured JSON format.

IMPORTANT:
- Accept transcription in ANY language (English, Spanish, French, etc.)
- Extract medical content WITHOUT translating it
- Respond ONLY with valid JSON, no additional explanations
- Use English field names (medical standard)

Return JSON structure with these exact fields:
{
  "subjetivo": {
    "motivo_consulta": "Chief complaint (main reason for consultation)",
    "historia_actual": "History of present illness (detailed symptom description)",
    "antecedentes": "Medical history (relevant past medical events)"
  },
  "objetivo": {
    "signos_vitales": "Vital signs (BP, temperature, heart rate, respiration rate)",
    "examen_fisico": "Physical examination findings"
  },
  "analisis": {
    "diagnosticos_diferenciales": ["Differential diagnosis 1", "Differential diagnosis 2"],
    "diagnostico_principal": "Primary diagnosis (most likely condition)"
  },
  "plan": {
    "tratamiento": "Treatment plan (medications and interventions)",
    "seguimiento": "Follow-up instructions",
    "estudios": ["Study 1", "Study 2"]
  }
}"""

            user_prompt = f"Medical consultation transcription:\n\n{transcription}"

            # Call Ollama
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                },
                timeout=120,
            )

            if response.status_code != 200:
                raise ValueError(f"Ollama request failed: {response.text}")

            result = response.json()
            response_text = result.get("response", "")

            # Parse JSON from response
            # Try to find JSON block in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                logger.warning(
                    "OLLAMA_NO_JSON_FOUND", response=response_text[:200]
                )
                # Return default structure
                return self._default_soap_structure()

            json_str = response_text[json_start:json_end]
            soap_data = json.loads(json_str)

            logger.info(
                "SOAP_EXTRACTED_FROM_OLLAMA",
                model=OLLAMA_MODEL,
                response_length=len(response_text),
            )

            return soap_data

        except Exception as e:
            logger.error("OLLAMA_EXTRACTION_FAILED", error=str(e))  # type: ignore[call-arg]
            # Return default structure on error
            return self._default_soap_structure()

    def _create_soap_note(self, job_id: str, soap_data: dict) -> SOAPNote:
        """Create SOAPNote model from extracted data.

        Args:
            job_id: Diarization job ID
            soap_data: Extracted SOAP data dictionary

        Returns:
            SOAPNote model instance
        """
        try:
            from backend.fi_consult_models import (
                Antecedentes,
                Habitos,
                SignosVitales,
            )

            # Extract sections with defaults
            subjetivo_data = soap_data.get("subjetivo", {})
            objetivo_data = soap_data.get("objetivo", {})
            analisis_data = soap_data.get("analisis", {})
            plan_data = soap_data.get("plan", {})

            # Parse antecedentes properly
            antecedentes_raw = subjetivo_data.get("antecedentes", {})
            if isinstance(antecedentes_raw, str):
                # If string, convert to dict
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

            # Create SOAP sections
            subjetivo = Subjetivo(
                motivo_consulta=subjetivo_data.get("motivo_consulta", ""),
                historia_actual=subjetivo_data.get("historia_actual", ""),
                antecedentes=antecedentes,
            )

            # Parse signos vitales properly
            signos_vitales_raw = objetivo_data.get("signos_vitales", {})
            if isinstance(signos_vitales_raw, str):
                signos_vitales_data = {"presion_arterial": signos_vitales_raw if signos_vitales_raw else None}
            else:
                signos_vitales_data = signos_vitales_raw or {}

            signos_vitales = SignosVitales(
                presion_arterial=signos_vitales_data.get("presion_arterial"),
                frecuencia_cardiaca=signos_vitales_data.get("frecuencia_cardiaca"),
                frecuencia_respiratoria=signos_vitales_data.get("frecuencia_respiratoria"),
                temperatura=signos_vitales_data.get("temperatura"),
                saturacion_oxigeno=signos_vitales_data.get("saturacion_oxigeno"),
                peso=signos_vitales_data.get("peso"),
            )

            # Parse exploracion fisica properly
            examen_fisico_raw = objetivo_data.get("examen_fisico", "")
            exploracion_fisica = ExploracionFisica(
                aspecto=examen_fisico_raw if examen_fisico_raw else "Examen físico realizado",
                cabeza_cuello=objetivo_data.get("cabeza_cuello"),
                torax=objetivo_data.get("torax"),
                cardiovascular=objetivo_data.get("cardiovascular"),
                pulmonar=objetivo_data.get("pulmonar"),
                abdomen=objetivo_data.get("abdomen"),
                extremidades=objetivo_data.get("extremidades"),
                neurologico=objetivo_data.get("neurologico"),
                piel=objetivo_data.get("piel"),
            )

            objetivo = Objetivo(
                signos_vitales=signos_vitales,
                exploracion_fisica=exploracion_fisica,
            )

            # Parse diagnostico_principal properly
            diagnostico_principal_raw = analisis_data.get("diagnostico_principal", "")
            if isinstance(diagnostico_principal_raw, str):
                diagnostico_principal = DiagnosticoPrincipal(
                    condicion=diagnostico_principal_raw or "Diagnóstico pendiente",
                    cie10="R69.9",  # Default ICD-10 for unspecified condition
                    evidencia=[],
                    probabilidad=0.5,
                    confianza=0.5,
                )
            else:
                diagnostico_principal = diagnostico_principal_raw

            # Parse diagnosticos diferenciales properly
            diferenciales_raw = analisis_data.get("diagnosticos_diferenciales", [])
            diagnosticos_diferenciales = []
            if isinstance(diferenciales_raw, list):
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

            # Create pronostico
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

            analisis = Analisis(
                diagnostico_principal=diagnostico_principal,
                diagnosticos_diferenciales=diagnosticos_diferenciales,
                factores_riesgo=analisis_data.get("factores_riesgo", []),
                senos_peligro=analisis_data.get("senos_peligro", []),
                pronostico=pronostico,
                razonamiento_clinico=analisis_data.get("razonamiento_clinico"),
            )

            # Parse seguimiento properly
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

            plan = Plan(
                tratamiento_farmacologico=[],
                tratamiento_no_farmacologico=[],
                estudios_adicionales=[],
                interconsultas=[],
                seguimiento=seguimiento,
            )

            # Create metadata
            metadata = SOAPMetadata(
                source="diarization_to_soap",
                model_used="ollama_mistral_mvp",
                completeness_score=self._calculate_completeness(
                    subjetivo, objetivo, analisis, plan
                ),
            )

            # Create final SOAP note
            soap_note = SOAPNote(
                consultation_id=job_id,
                subjetivo=subjetivo,
                objetivo=objetivo,
                analisis=analisis,
                plan=plan,
                metadata=metadata,
                completeness=metadata.completeness_score,
            )

            return soap_note

        except ValidationError as e:
            logger.error(
                "SOAP_VALIDATION_FAILED", job_id=job_id, errors=str(e)
            )  # type: ignore[call-arg]
            raise

    def _calculate_completeness(
        self, subjetivo: Subjetivo, objetivo: Objetivo, analisis: Analisis, plan: Plan
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
        max_score = 100.0

        # Check each section
        if subjetivo.motivo_consulta:
            score += 15
        if subjetivo.historia_actual:
            score += 10
        if objetivo.signos_vitales:
            score += 15
        if objetivo.examen_fisico:
            score += 10
        if analisis.diagnostico_principal:
            score += 20
        if analisis.diagnosticos_diferenciales:
            score += 10
        if plan.tratamiento:
            score += 15

        return min(score, max_score)

    def _default_soap_structure(self) -> dict:
        """Return default empty SOAP structure.

        Returns:
            Dictionary with SOAP structure
        """
        return {
            "subjetivo": {
                "motivo_consulta": "",
                "historia_actual": "",
                "antecedentes": "",
            },
            "objetivo": {"signos_vitales": "", "examen_fisico": ""},
            "analisis": {"diagnosticos_diferenciales": [], "diagnostico_principal": ""},
            "plan": {"tratamiento": "", "seguimiento": "", "estudios": []},
        }
