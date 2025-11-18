"""
Pydantic schemas para Internal LLM API
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


class ChatRequest(BaseModel):
    """Request para chat conversacional con Free-Intelligence."""

    persona: str = Field(
        ...,
        description="Modo del asistente: onboarding_guide, clinical_advisor, soap_editor",
        examples=["onboarding_guide", "clinical_advisor", "soap_editor"],
    )
    message: str = Field(..., min_length=1, max_length=5000)
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Contexto adicional (patient_id, session_id, soap_data, etc.)",
    )
    session_id: Optional[str] = Field(default=None, description="Session ID para audit logging")


class ChatResponse(BaseModel):
    """Response con logging ultra detallado."""

    response: str
    persona: str
    tokens_used: int
    latency_ms: int
    model: str

    # Observability metadata
    prompt_hash: str = Field(description="SHA256 del prompt enviado (primeros 12 chars)")
    response_hash: str = Field(description="SHA256 de la respuesta (primeros 12 chars)")
    logged_at: str = Field(description="Timestamp ISO8601")


# ============================================================================
# STRUCTURED EXTRACTION ENDPOINTS
# ============================================================================


class StructuredRequest(BaseModel):
    """Request para extracción estructurada via LLM."""

    persona: str = Field(..., description="Modo del asistente")
    command: str = Field(..., min_length=1, description="Comando en lenguaje natural")
    context: dict[str, Any] = Field(..., description="Contexto necesario (ej: current_soap)")
    output_schema: dict[str, str] = Field(..., description="Schema esperado del JSON de salida")
    session_id: Optional[str] = Field(default=None, description="Session ID para audit")


class StructuredResponse(BaseModel):
    """Response con datos estructurados + observabilidad."""

    data: dict[str, Any] = Field(description="Datos extraídos según schema")
    explanation: str = Field(description="Explicación de lo que se hizo")
    tokens_used: int
    latency_ms: int
    model: str

    # Observability
    prompt_hash: str
    response_hash: str
    logged_at: str
