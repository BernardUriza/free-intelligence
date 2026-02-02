"""
LLM Middleware Service - HTTP/CLI LLM Interface for Free Intelligence

This service provides a centralized LLM interface that implements the policies
required by Free Intelligence (privacy, cost control, audit trails).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import os
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older Python versions
    from backports.zoneinfo import ZoneInfo

import structlog
from fastapi import FastAPI, HTTPException
from langdetect import LangDetectException, detect
from pydantic import BaseModel

from ..providers.llm import llm_generate
from ..schemas.llm_audit_policy import require_audit_log


def detect_language(text: str) -> str:
    """
    Detect the language of the given text.

    Args:
        text: Input text to detect language for

    Returns:
        ISO 639-1 language code (e.g., 'es', 'en', etc.) or 'es' as default if detection fails
    """
    try:
        detected_lang = detect(text)
        return detected_lang
    except LangDetectException:
        # If language detection fails, return default language 'es'
        logger.warning("LANGUAGE_DETECTION_FAILED", text_preview=text[:50])
        return "es"


def get_language_instruction(lang: str) -> str:
    """
    Get the language instruction for the LLM based on the detected language.

    Args:
        lang: ISO 639-1 language code

    Returns:
        Instruction string to inject into the prompt
    """
    language_instructions = {
        "es": "IMPORTANTE: Responde en español.",
        "en": "IMPORTANT: Respond in English.",
        "fr": "IMPORTANT: Répondez en français.",
        "de": "WICHTIG: Antworten Sie auf Deutsch.",
        "it": "IMPORTANTE: Rispondi in italiano.",
        "pt": "IMPORTANTE: Responda em português.",
        "zh-cn": "重要：用中文回答。",
        "ja": "重要：日本語で答えてください。",
        "ko": "중요: 한국어로 대답하세요.",
        "ru": "ВАЖНО: Отвечайте на русском языке.",
        "ar": "مهم: أجب باللغة العربية.",
        "hi": "महत्वपूर्ण: हिंदी में उत्तर दें।",
    }

    # Return the instruction for the detected language, or default to Spanish
    return language_instructions.get(lang, "IMPORTANTE: Responde en español.")


def get_logger(
    name: str = "llm-middleware",
    log_level: str = "INFO",
    timezone: str = "America/Mexico_City",
) -> structlog.BoundLogger:
    """
    Get configured structured logger with timezone-aware timestamps.
    Simplified version that doesn't depend on config_loader.
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,
    )

    # Timezone-aware timestamp processor
    def add_timestamp(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Add timezone-aware timestamp to log entries."""
        tz = ZoneInfo(timezone)
        event_dict["timestamp"] = datetime.now(tz).isoformat()
        return event_dict

    # Configure structlog with KeyValueRenderer for compatibility with keyword arguments
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.KeyValueRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


# Configure structlog
logger = get_logger()

# App initialization
app = FastAPI(
    title="Free Intelligence - LLM Middleware",
    description="Centralized LLM interface with policy enforcement",
    version="0.1.0",
)


# Pydantic models
class LLMGenerateRequest(BaseModel):
    """Request model for LLM generation"""

    prompt: str
    provider: str = "claude"  # Default to Claude
    model: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.7
    # Additional parameters can be added as needed


class LLMGenerateResponse(BaseModel):
    """Response model for LLM generation"""

    content: str
    provider: str
    model: str
    tokens_used: int | None = None
    timestamp: str


class StructuredExtractRequest(BaseModel):
    """Request model for structured data extraction"""

    text: str
    schema_definition: dict[str, Any]
    provider: str = "claude"
    temperature: float = 0.3  # Lower temperature for more consistent structured output


class StructuredResponse(BaseModel):
    """Response model for structured data extraction"""

    extracted_data: dict[str, Any]
    provider: str
    success: bool
    message: str | None = None


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "llm-middleware",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint placeholder"""
    # In a real implementation, this would return Prometheus metrics
    return {"message": "Metrics endpoint not implemented", "status": "placeholder"}


@app.get("/metrics/json")
async def get_metrics_json():
    """JSON metrics endpoint placeholder"""
    # In a real implementation, this would return metrics in JSON format
    return {"metrics": {}, "status": "placeholder"}


@app.post("/llm/generate", response_model=LLMGenerateResponse)
@require_audit_log
async def generate_text(request: LLMGenerateRequest) -> LLMGenerateResponse:
    """Generate text using the specified LLM provider.

    This endpoint implements the LLM Router Policy by centralizing all LLM access
    and enforcing audit logging, cost controls, and privacy policies.
    """
    try:
        # Detect language of the input prompt
        detected_lang = detect_language(request.prompt)
        language_instruction = get_language_instruction(detected_lang)

        logger.info(
            "LLM_GENERATE_REQUEST",
            provider=request.provider,
            prompt_preview=request.prompt[:50] + ("..." if len(request.prompt) > 50 else ""),
            detected_language=detected_lang,
        )

        # Inject language instruction at the beginning of the prompt
        augmented_prompt = f"{language_instruction}\n\n{request.prompt}"

        # Call the unified LLM interface with the augmented prompt
        response = llm_generate(
            prompt=augmented_prompt,
            provider=request.provider,
            provider_config={"model": request.model} if request.model else None,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        logger.info("LLM_GENERATE_SUCCESS", provider=request.provider)

        return LLMGenerateResponse(
            content=response.content,
            provider=request.provider,
            model=response.model or request.model or "unknown",
            tokens_used=response.tokens_used,
            timestamp=datetime.now(UTC).isoformat(),
        )

    except Exception as e:
        logger.error("LLM_GENERATE_ERROR", error=str(e), provider=request.provider)
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e!s}")


@app.post("/llm/structured-extract", response_model=StructuredResponse)
@require_audit_log
async def structured_extract(request: StructuredExtractRequest) -> StructuredResponse:
    """Extract structured data from text using LLM.

    This endpoint is used by various parts of the system that need structured
    output from LLMs, with appropriate privacy and audit controls.
    """
    try:
        logger.info(
            "STRUCTURED_EXTRACT_REQUEST",
            provider=request.provider,
            schema_keys=list(request.schema_definition.keys()),
        )

        # Create a prompt for structured extraction
        schema_description = "\n".join(
            [f"- {key}: {value}" for key, value in request.schema_definition.items()]
        )

        prompt = f"""
        Extract the following structured information from the provided text:
        {schema_description}

        Text: {request.text}

        Respond with a JSON object containing only the requested fields.
        If information is not available for a field, use null as the value.
        """

        # Use the provider specified in the request, or the system default
        provider_to_use = request.provider

        response = llm_generate(
            prompt=prompt,
            provider=provider_to_use,
            # Note: temperature is not supported by llm_generate function
            # We'll pass it in **kwargs to allow for future implementation
            temperature=request.temperature,
        )

        import json

        try:
            extracted_data = json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("STRUCTURED_EXTRACT_JSON_ERROR", response_content=response.content)
            raise ValueError("LLM response was not valid JSON")

        logger.info("STRUCTURED_EXTRACT_SUCCESS", provider=request.provider)

        return StructuredResponse(
            extracted_data=extracted_data,
            provider=request.provider,
            success=True,
            message="Structured extraction completed successfully",
        )

    except Exception as e:
        logger.error("STRUCTURED_EXTRACT_ERROR", error=str(e), provider=request.provider)
        return StructuredResponse(
            extracted_data={},
            provider=request.provider,
            success=False,
            message=f"Structured extraction failed: {e!s}",
        )


@app.post("/chat")
async def chat_endpoint() -> dict[str, str]:
    """Chat endpoint placeholder.

    This would implement a chat-based interface using the LLM router.
    """
    return {"message": "Chat endpoint not implemented", "status": "placeholder"}


if __name__ == "__main__":
    import uvicorn

    # This allows running the middleware as a standalone service
    port = int(os.getenv("LLM_MIDDLEWARE_PORT", 9001))
    host = os.getenv("LLM_MIDDLEWARE_HOST", "0.0.0.0")

    uvicorn.run(
        "backend.llm_middleware:app",
        host=host,
        port=port,
        reload=True,
        log_config=None,  # Use structlog configuration
    )
