"""Waiting Room Content Generation - AI-powered health tips and trivia.

Dynamic content generation for waiting room TV displays using LLM.

Endpoints:
- POST /generate-tip - Generate health tip
- POST /generate-trivia - Generate health trivia

Migrated from: backend/api/routers/workflow/public/waiting_room.py
"""

from __future__ import annotations

import time
from typing import Literal

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.clients import get_llm_client
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.observability.logging import CTX_REQUEST_ID
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class GenerateTipRequest(BaseModel):
    """Request for health tip generation."""

    category: Literal["nutrition", "exercise", "mental_health", "prevention"] = Field(
        ..., description="Category of health tip to generate"
    )
    context: str | None = Field(
        None,
        description="Optional context (time of day, season, specialty)",
    )


class GenerateTipResponse(BaseModel):
    """Health tip response."""

    tip: str = Field(..., description="Generated health tip (1-2 sentences)")
    category: str = Field(..., description="Category of the tip")
    generated_by: str = Field(default="FI", description="Always 'FI' for AI-generated")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    latency_ms: int = Field(default=0, description="Generation latency in milliseconds")


class GenerateTriviaRequest(BaseModel):
    """Request for health trivia generation."""

    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="easy", description="Difficulty level"
    )


class TriviaOption(BaseModel):
    """Trivia answer option."""

    text: str
    is_correct: bool


class GenerateTriviaResponse(BaseModel):
    """Health trivia response."""

    question: str = Field(..., description="Trivia question")
    options: list[str] = Field(..., description="4 answer options")
    correct_answer: int = Field(..., description="Index of correct answer (0-3)")
    explanation: str = Field(..., description="Why the answer is correct")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    latency_ms: int = Field(default=0, description="Generation latency in milliseconds")


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/generate-tip",
    response_model=GenerateTipResponse,
    tags=["Waiting Room"],
    summary="Generate health tip for TV display",
)
async def generate_health_tip(
    request: GenerateTipRequest,
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> GenerateTipResponse:
    """Generate a health tip for waiting room display using AI."""
    start_time = time.perf_counter()

    try:
        request_id = CTX_REQUEST_ID.get() or None
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())
            CTX_REQUEST_ID.set(request_id)

        category_prompts = {
            "nutrition": "nutrición saludable y alimentación balanceada",
            "exercise": "actividad física y ejercicio",
            "mental_health": "salud mental y bienestar emocional",
            "prevention": "prevención de enfermedades y cuidado preventivo",
        }

        context_str = f" Contexto: {request.context}." if request.context else ""

        message = (
            f"Genera un tip breve de salud sobre {category_prompts[request.category]} "
            f"para mostrar en TV de sala de espera.{context_str} "
            "Debe ser 1-2 oraciones, práctico, basado en evidencia médica, "
            "y fácil de entender para pacientes. "
            "Responde SOLO con el tip, sin introducción."
        )

        llm_client = get_llm_client()

        response = await llm_client.chat(
            persona="general_assistant",
            message=message,
            context={"category": request.category, "purpose": "health_tip_generation"},
            request_id=request_id,
            caller="public",
        )

        tip_text = response.get("response", "")
        tokens_used = response.get("tokens_used", 0)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "Generated health tip",
            category=request.category,
            tokens=tokens_used,
            latency_ms=latency_ms,
        )

        return GenerateTipResponse(
            tip=tip_text.strip(),
            category=request.category,
            generated_by="FI",
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    except Exception as e:
        audit_service.log_action(
            action="health_tip_generation_failed",
            user_id=current_user.id,
            resource="waiting_room_content",
            result="failure",
            details={"error": str(e), "category": request.category, "context": request.context},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate health tip: {e!s}",
        )


@router.post(
    "/generate-trivia",
    response_model=GenerateTriviaResponse,
    tags=["Waiting Room"],
    summary="Generate health trivia for TV display",
)
async def generate_health_trivia(
    request: GenerateTriviaRequest,
) -> GenerateTriviaResponse:
    """Generate a health trivia question for waiting room display using AI."""
    start_time = time.perf_counter()

    try:
        difficulty_hints = {
            "easy": "conocimiento general básico de salud",
            "medium": "requiere algo de conocimiento de salud",
            "hard": "requiere conocimiento más profundo",
        }

        command = (
            f"Genera una pregunta de trivia de salud de dificultad {request.difficulty} "
            f"({difficulty_hints[request.difficulty]}) para mostrar en TV de sala de espera. "
            "La pregunta debe ser educativa, apropiada para audiencias generales, e incluir 4 opciones. "
            "IMPORTANTE: correct_answer es el índice (0-3) de la respuesta correcta en el array options."
        )

        output_schema = {
            "question": "str - La pregunta de trivia",
            "options": "list[str] - 4 opciones de respuesta",
            "correct_answer": "int - Índice (0-3) de la respuesta correcta",
            "explanation": "str - Explicación breve (1-2 oraciones) de por qué es correcta",
        }

        llm_client = get_llm_client()

        response = await llm_client.structured_extract(
            persona="general_assistant",
            command=command,
            context={"difficulty": request.difficulty, "purpose": "trivia_generation"},
            output_schema=output_schema,
        )

        trivia_data = response.get("data", {})
        tokens_used = response.get("tokens_used", 0)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "Generated health trivia",
            difficulty=request.difficulty,
            tokens=tokens_used,
            latency_ms=latency_ms,
        )

        return GenerateTriviaResponse(
            question=trivia_data["question"],
            options=trivia_data["options"],
            correct_answer=trivia_data["correct_answer"],
            explanation=trivia_data["explanation"],
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error("Failed to generate health trivia", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate health trivia: {e!s}",
        )
