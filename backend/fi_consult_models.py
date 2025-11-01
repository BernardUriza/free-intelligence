from __future__ import annotations

"""
Free Intelligence - Consultation Models

Pydantic models for SOAP-based medical consultations with event-sourcing.
Based on NOM-004-SSA3-2012 (Mexican medical standard).

File: backend/fi_consult_models.py
Created: 2025-10-28
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# ENUMS
# ============================================================================


class MessageRole(str, Enum):
    """Message role in consultation."""

    USER = "user"
    ASSISTANT = "assistant"


class Severity(str, Enum):
    """Symptom severity levels."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class Gender(str, Enum):
    """Patient gender."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class UrgencyLevel(str, Enum):
    """Urgency classification levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Gravedad(str, Enum):
    """Gravedad (gravity) levels for differential diagnoses."""

    BAJA = "baja"
    MODERADA = "moderada"
    ALTA = "alta"
    CRITICA = "critica"


class UrgenciaTriaje(str, Enum):
    """Urgency triage categories (NOM-004 compatible)."""

    NO_URGENTE = "no_urgente"
    SEMI_URGENTE = "semi_urgente"
    URGENTE = "urgente"
    EMERGENCIA = "emergencia"


class EstudioUrgencia(str, Enum):
    """Urgency level for diagnostic studies."""

    STAT = "stat"  # Immediate
    URGENTE = "urgente"  # Within 1-2 hours
    RUTINA = "rutina"  # Routine scheduling


class EventType(str, Enum):
    """Domain event types (from MAPPING.json)."""

    # Consultation lifecycle
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    MESSAGE_UPDATED = "MESSAGE_UPDATED"
    MESSAGE_DELETED = "MESSAGE_DELETED"
    MESSAGE_PROCESSED = "MESSAGE_PROCESSED"
    MESSAGES_CLEARED = "MESSAGES_CLEARED"
    CONSULTATION_RESET = "CONSULTATION_RESET"
    CONSULTATION_COMMITTED = "CONSULTATION_COMMITTED"

    # Extraction
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_ITERATION_INCREMENTED = "EXTRACTION_ITERATION_INCREMENTED"
    EXTRACTION_PROCESS_COMPLETED = "EXTRACTION_PROCESS_COMPLETED"

    # WIP Data
    DEMOGRAPHICS_UPDATED = "DEMOGRAPHICS_UPDATED"
    SYMPTOMS_UPDATED = "SYMPTOMS_UPDATED"
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    COMPLETENESS_CALCULATED = "COMPLETENESS_CALCULATED"

    # SOAP
    SOAP_GENERATION_STARTED = "SOAP_GENERATION_STARTED"
    SOAP_SECTION_COMPLETED = "SOAP_SECTION_COMPLETED"
    SOAP_GENERATION_COMPLETED = "SOAP_GENERATION_COMPLETED"
    SOAP_GENERATION_FAILED = "SOAP_GENERATION_FAILED"

    # Urgency
    CRITICAL_PATTERN_DETECTED = "CRITICAL_PATTERN_DETECTED"
    URGENCY_CLASSIFIED = "URGENCY_CLASSIFIED"

    # LLM
    LLM_CALL_INITIATED = "LLM_CALL_INITIATED"
    LLM_CALL_COMPLETED = "LLM_CALL_COMPLETED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"

    # Audit
    AUDIT_ENTRY_CREATED = "AUDIT_ENTRY_CREATED"

    # System
    CORE_STATE_CHANGED = "CORE_STATE_CHANGED"
    CORE_ERROR_OCCURRED = "CORE_ERROR_OCCURRED"


# ============================================================================
# PATIENT & DEMOGRAPHICS
# ============================================================================


class PatientStub(BaseModel):
    """
    Patient identification stub (non-PHI).
    For demo/MVP - does not include full patient record.
    """

    patient_id: Optional[str] = Field(
        default=None, description="De-identified patient ID (not real PHI)"
    )
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[Gender] = None
    weight: Optional[float] = Field(default=None, ge=0, description="Weight in kg")
    height: Optional[float] = Field(default=None, ge=0, description="Height in cm")
    occupation: Optional[str] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """Validate age is reasonable."""
        if v is not None and (v < 0 or v > 120):
            raise ValueError("Age must be between 0 and 120")
        return v


class Demographics(BaseModel):
    """Demographics extracted from conversation."""

    age: Optional[int] = None
    gender: Optional[Gender] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    occupation: Optional[str] = None


class Symptoms(BaseModel):
    """Symptom data structure."""

    primary_symptoms: list[str] = Field(default_factory=list)
    secondary_symptoms: Optional[list[str]] = None
    duration: Optional[str] = None
    severity: Optional[Severity] = None
    location: Optional[str] = None
    quality: Optional[str] = None
    aggravating_factors: Optional[list[str]] = None
    relieving_factors: Optional[list[str]] = None


class MedicalContext(BaseModel):
    """Medical history and context."""

    past_medical_history: Optional[list[str]] = None
    family_history: Optional[list[str]] = None
    medications: Optional[list[str]] = None
    allergies: Optional[list[str]] = None
    surgeries: Optional[list[str]] = None


# ============================================================================
# SOAP COMPONENTS (NOM-004-SSA3-2012)
# ============================================================================


class Antecedentes(BaseModel):
    """Antecedentes médicos (Medical history)."""

    personales: list[str] = Field(default_factory=list)
    familiares: list[str] = Field(default_factory=list)
    medicamentos: list[str] = Field(default_factory=list)
    alergias: list[str] = Field(default_factory=list)
    quirurgicos: list[str] = Field(default_factory=list)


class Habitos(BaseModel):
    """Hábitos y estilo de vida (Lifestyle habits)."""

    tabaquismo: Optional[str] = None
    alcoholismo: Optional[str] = None
    drogas: Optional[str] = None
    ejercicio: Optional[str] = None
    dieta: Optional[str] = None


class Subjetivo(BaseModel):
    """S - Subjetivo (Subjective) section."""

    motivo_consulta: str = Field(description="Chief complaint")
    historia_actual: str = Field(description="Present illness history")
    antecedentes: Antecedentes
    revision_sistemas: Optional[str] = None
    contexto_psicosocial: Optional[str] = None
    habitos: Optional[Habitos] = None


class SignosVitales(BaseModel):
    """Signos vitales (Vital signs)."""

    presion_arterial: Optional[str] = None
    frecuencia_cardiaca: Optional[int] = None
    frecuencia_respiratoria: Optional[int] = None
    temperatura: Optional[float] = None
    saturacion_oxigeno: Optional[float] = None
    peso: Optional[float] = None
    talla: Optional[float] = None
    imc: Optional[float] = None
    glucosa: Optional[float] = None


class ExploracionFisica(BaseModel):
    """Exploración física (Physical examination)."""

    aspecto: str
    cabeza_cuello: Optional[str] = None
    torax: Optional[str] = None
    cardiovascular: Optional[str] = None
    pulmonar: Optional[str] = None
    abdomen: Optional[str] = None
    extremidades: Optional[str] = None
    neurologico: Optional[str] = None
    piel: Optional[str] = None


class Objetivo(BaseModel):
    """O - Objetivo (Objective) section."""

    signos_vitales: SignosVitales
    exploracion_fisica: ExploracionFisica
    estudios_complementarios: Optional[dict[str, Any]] = None


class DiagnosticoPrincipal(BaseModel):
    """Diagnóstico principal (Primary diagnosis)."""

    condicion: str
    cie10: str = Field(description="ICD-10 code")
    evidencia: list[str] = Field(default_factory=list)
    probabilidad: float = Field(ge=0, le=1)
    confianza: float = Field(ge=0, le=1)


class DiagnosticoDiferencial(BaseModel):
    """Diagnóstico diferencial (Differential diagnosis)."""

    condicion: str
    cie10: str
    probabilidad: float = Field(ge=0, le=1)
    gravedad: Gravedad
    urgencia: UrgenciaTriaje
    defensive_score: float = Field(
        description="Defensive score = gravity * 0.7 + probability * 0.3"
    )
    evidencia: list[str] = Field(default_factory=list)
    descartar_mediante: list[str] = Field(default_factory=list)


class Pronostico(BaseModel):
    """Pronóstico (Prognosis)."""

    inmediato: str
    corto: str
    largo: str


class Analisis(BaseModel):
    """A - Análisis (Assessment) section."""

    diagnostico_principal: DiagnosticoPrincipal
    diagnosticos_diferenciales: list[DiagnosticoDiferencial]
    factores_riesgo: list[str] = Field(default_factory=list)
    senos_peligro: list[str] = Field(
        default_factory=list, description="Red flags (widow maker patterns)"
    )
    pronostico: Pronostico
    razonamiento_clinico: Optional[str] = None


class TratamientoFarmacologico(BaseModel):
    """Tratamiento farmacológico (Pharmacological treatment)."""

    medicamento: str
    dosis: str
    via: str
    frecuencia: str
    duracion: str
    indicacion: str


class TratamientoNoFarmacologico(BaseModel):
    """Tratamiento no farmacológico (Non-pharmacological treatment)."""

    intervencion: str
    frecuencia: str
    duracion: str
    objetivo: str


class EstudioAdicional(BaseModel):
    """Estudio adicional (Additional study/lab/imaging)."""

    estudio: str
    urgencia: EstudioUrgencia
    justificacion: str
    esperado: str


class Interconsulta(BaseModel):
    """Interconsulta (Specialist referral)."""

    especialidad: str
    urgencia: EstudioUrgencia
    motivo: str


class Seguimiento(BaseModel):
    """Seguimiento (Follow-up plan)."""

    proxima_cita: str
    vigilar: list[str] = Field(default_factory=list)
    criterios_emergencia: list[str] = Field(default_factory=list)
    educacion_paciente: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """P - Plan section."""

    tratamiento_farmacologico: list[TratamientoFarmacologico] = Field(default_factory=list)
    tratamiento_no_farmacologico: list[TratamientoNoFarmacologico] = Field(default_factory=list)
    estudios_adicionales: list[EstudioAdicional] = Field(default_factory=list)
    interconsultas: list[Interconsulta] = Field(default_factory=list)
    seguimiento: Seguimiento
    criterios_hospitalizacion: Optional[list[str]] = None


class SOAPMetadata(BaseModel):
    """SOAP note metadata."""

    medico: str
    especialidad: str
    fecha: datetime
    duracion_consulta: int = Field(description="Duration in minutes")
    consentimiento_informado: bool
    version_nom: str = Field(default="NOM-004-SSA3-2012")


class SOAPNote(BaseModel):
    """
    Complete SOAP note (NOM-004-SSA3-2012 compliant).
    Structured medical note for consultation.
    """

    consultation_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique consultation identifier"
    )
    subjetivo: Subjetivo
    objetivo: Objetivo
    analisis: Analisis
    plan: Plan
    metadata: SOAPMetadata

    # Quality metrics
    quality_score: Optional[float] = Field(default=None, ge=0, le=1)
    completeness: Optional[float] = Field(default=None, ge=0, le=100)
    nom_compliance: Optional[float] = Field(default=None, ge=0, le=100)


# ============================================================================
# EVENTS
# ============================================================================


class EventMetadata(BaseModel):
    """Event metadata for audit and traceability."""

    source: str = Field(default="fi_consultation_service")
    user_id: str
    session_id: str
    timezone: str = Field(default="America/Mexico_City")


class ConsultationEvent(BaseModel):
    """
    Base domain event for event-sourcing.
    All consultation events inherit from this.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    consultation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    payload: dict[str, Any]
    metadata: EventMetadata

    # For audit compliance
    audit_hash: Optional[str] = Field(
        default=None, description="SHA256 hash of payload for non-repudiation"
    )


class MessageReceivedEvent(ConsultationEvent):
    """Event: User or assistant message received."""

    event_type: EventType = EventType.MESSAGE_RECEIVED

    class PayloadSchema(BaseModel):
        message_content: str
        message_role: MessageRole
        metadata: Optional[dict[str, Any]] = None


class ExtractionStartedEvent(ConsultationEvent):
    """Event: Medical data extraction started."""

    event_type: EventType = EventType.EXTRACTION_STARTED

    class PayloadSchema(BaseModel):
        iteration: int = Field(ge=1, le=5)
        context_message_count: int
        has_previous_extraction: bool


class ExtractionCompletedEvent(ConsultationEvent):
    """Event: Medical data extraction completed."""

    event_type: EventType = EventType.EXTRACTION_COMPLETED

    class PayloadSchema(BaseModel):
        iteration: int
        completeness: float = Field(ge=0, le=100)
        nom_compliance: float = Field(ge=0, le=100)
        missing_fields: list[str]
        extraction_data: dict[str, Any]


class SOAPGenerationCompletedEvent(ConsultationEvent):
    """Event: SOAP note generation completed."""

    event_type: EventType = EventType.SOAP_GENERATION_COMPLETED

    class PayloadSchema(BaseModel):
        soap_data: dict[str, Any]  # Full SOAP structure
        quality_score: float = Field(ge=0, le=1)
        ready_for_commit: bool


class CriticalPatternDetectedEvent(ConsultationEvent):
    """Event: Life-threatening pattern detected."""

    event_type: EventType = EventType.CRITICAL_PATTERN_DETECTED

    class PayloadSchema(BaseModel):
        pattern_name: str
        gravity_score: int = Field(ge=1, le=10)
        widow_maker_alert: bool
        symptoms_matched: list[str]
        critical_differentials: list[str]
        time_to_action: str


class ConsultationCommittedEvent(ConsultationEvent):
    """Event: SOAP note committed (final, immutable)."""

    event_type: EventType = EventType.CONSULTATION_COMMITTED

    class PayloadSchema(BaseModel):
        soap_data: dict[str, Any]
        committed_by: str
        commit_hash: str = Field(description="SHA256 of SOAP data")
        quality_score: float
        completeness: float
        nom_compliance: float


# ============================================================================
# CONSULTATION AGGREGATE
# ============================================================================


class CompletenessMetrics(BaseModel):
    """Completeness metrics for extraction/SOAP."""

    percentage: float = Field(ge=0, le=100)
    sections: Optional[dict[str, float]] = None
    critical_fields_present: list[str] = Field(default_factory=list)
    critical_fields_missing: list[str] = Field(default_factory=list)
    nom_compliance: float = Field(ge=0, le=100)
    nom_violations: list[str] = Field(default_factory=list)
    ready_for_commit: bool


class UrgencyAssessment(BaseModel):
    """Urgency assessment result."""

    urgency_level: UrgencyLevel
    gravity_score: int = Field(ge=1, le=10)
    time_to_action: str
    identified_patterns: list[dict[str, Any]] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)


class Consultation(BaseModel):
    """
    Consultation aggregate root.
    Reconstructed from event stream.
    """

    consultation_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Current state
    messages: list[dict[str, Any]] = Field(default_factory=list)
    patient_data: Optional[PatientStub] = None
    extraction_data: Optional[dict[str, Any]] = None
    soap_note: Optional[SOAPNote] = None
    urgency_assessment: Optional[UrgencyAssessment] = None

    # Metrics
    completeness: Optional[CompletenessMetrics] = None
    extraction_iteration: int = Field(default=0, ge=0, le=5)
    is_committed: bool = Field(default=False)
    commit_hash: Optional[str] = None

    # Event stream
    event_count: int = Field(default=0, ge=0)
    last_event_id: Optional[str] = None

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================


class StartConsultationRequest(BaseModel):
    """Request to start a new consultation."""

    user_id: str
    patient_stub: Optional[PatientStub] = None


class StartConsultationResponse(BaseModel):
    """Response when consultation started."""

    consultation_id: str
    session_id: str
    created_at: datetime


class AppendEventRequest(BaseModel):
    """Request to append event to consultation."""

    event_type: EventType
    payload: dict[str, Any]
    user_id: str


class AppendEventResponse(BaseModel):
    """Response after event appended."""

    event_id: str
    consultation_id: str
    event_count: int
    timestamp: datetime


class GetConsultationResponse(BaseModel):
    """Response with full consultation state."""

    consultation: Consultation


class GetSOAPResponse(BaseModel):
    """Response with SOAP note view."""

    consultation_id: str
    soap_note: Optional[SOAPNote]
    completeness: Optional[CompletenessMetrics]
    urgency_assessment: Optional[UrgencyAssessment]
    is_ready_for_commit: bool
