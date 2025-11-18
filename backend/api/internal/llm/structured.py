"""
Internal Structured Extraction Endpoint

Para comandos que retornan JSON estructurado (como SOAP modifications).
Provee ultra observabilidad con parsing JSON robusto.
"""

import hashlib
import json
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.schemas.llm_audit_policy import require_audit_log
from backend.services.llm.persona_manager import PersonaManager

from .schemas import StructuredRequest, StructuredResponse

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = PersonaManager()


@router.post("/structured-extract", response_model=StructuredResponse)
@require_audit_log
async def internal_structured_extract(request: StructuredRequest) -> StructuredResponse:
    """INTERNAL: Extract structured data via LLM (ultra observable).

    Usado para comandos que necesitan respuestas estructuradas en JSON:
    - Modificaciones a SOAP notes
    - Extracción de datos clínicos
    - Cualquier operación que requiera schema validation

    Args:
        request: Command + context + output_schema

    Returns:
        StructuredResponse con JSON parseado + observabilidad

    Raises:
        400: Invalid persona or schema
        500: LLM failed or JSON parsing failed
    """
    start_time = time.time()
    prompt = ""
    response_text = ""

    try:
        # Get persona configuration
        try:
            persona_config = persona_mgr.get_persona(request.persona)
        except ValueError as e:
            logger.warning(
                "INTERNAL_LLM_INVALID_PERSONA",
                persona=request.persona,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # Build prompt for structured extraction
        prompt = f"""{persona_config.system_prompt}

Context:
{json.dumps(request.context, indent=2)}

User command: "{request.command}"

Expected output schema:
{json.dumps(request.output_schema, indent=2)}

Your task:
1. Parse the user's command
2. Determine what structured updates are needed
3. Return ONLY valid JSON matching the schema (no markdown, no explanations outside JSON)

Respond with JSON in this exact format:
{{
  "data": {{ ... }},
  "explanation": "Brief explanation of what was done"
}}"""

        # Hash for audit
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        logger.info(
            "INTERNAL_LLM_STRUCTURED_START",
            persona=request.persona,
            command_length=len(request.command),
            schema_fields=list(request.output_schema.keys()),
            prompt_hash=prompt_hash[:12],
            session_id=request.session_id,
        )

        # Call LLM
        llm_response = llm_generate(
            prompt,
            temperature=persona_config.temperature,
            max_tokens=persona_config.max_tokens,
        )

        response_text = llm_response.content.strip()
        response_hash = hashlib.sha256(response_text.encode()).hexdigest()

        logger.debug(
            "INTERNAL_LLM_STRUCTURED_RESPONSE_RAW",
            response_preview=response_text[:200],
            response_length=len(response_text),
        )

        # Parse JSON response (robust extraction)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            logger.error(
                "INTERNAL_LLM_STRUCTURED_NO_JSON",
                response_text=response_text[:500],
            )
            raise ValueError("No JSON found in LLM response")

        json_str = response_text[json_start:json_end]

        try:
            parsed_response = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(
                "INTERNAL_LLM_STRUCTURED_JSON_INVALID",
                json_str=json_str[:500],
                error=str(e),
            )
            raise ValueError(f"Invalid JSON in response: {e}") from e

        # Validate response structure
        if "data" not in parsed_response:
            logger.error(
                "INTERNAL_LLM_STRUCTURED_MISSING_DATA",
                keys=list(parsed_response.keys()),
            )
            raise ValueError("Response missing 'data' field")

        if "explanation" not in parsed_response:
            # Add default explanation if missing
            parsed_response["explanation"] = "Data extracted successfully"

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract metadata
        tokens_used = 0
        model_name = "unknown"
        if hasattr(llm_response, "usage") and llm_response.usage:
            tokens_used = llm_response.usage.total_tokens
        if hasattr(llm_response, "model"):
            model_name = llm_response.model

        logger.info(
            "INTERNAL_LLM_STRUCTURED_SUCCESS",
            persona=request.persona,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            data_fields=list(parsed_response["data"].keys()),
            prompt_hash=prompt_hash[:12],
            response_hash=response_hash[:12],
            session_id=request.session_id,
        )

        return StructuredResponse(
            data=parsed_response["data"],
            explanation=parsed_response["explanation"],
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model=model_name,
            prompt_hash=prompt_hash[:12],
            response_hash=response_hash[:12],
            logged_at=datetime.now(UTC).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "INTERNAL_LLM_STRUCTURED_FAILED",
            persona=request.persona,
            command=request.command[:100],
            error=str(e),
            error_type=type(e).__name__,
            response_text=response_text[:500] if response_text else "N/A",
            session_id=request.session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Structured extraction failed: {e!s}",
        ) from e
