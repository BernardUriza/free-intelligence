"""Internal Structured Extraction Endpoint.

For commands that return structured JSON (like SOAP modifications).
Provides ultra observability with robust JSON parsing.

Endpoint:
- POST /llm/structured-extract - Extract structured data via LLM

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Infrastructure Migration)
"""

import hashlib
import json
import re
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from backend.providers import llm_generate
from backend.schemas.llm.audit_policy import require_audit_log
from backend.services.llm.dependencies import get_persona_manager
from backend.utils.common.logging.logger import get_logger

from .schemas import StructuredRequest, StructuredResponse

router = APIRouter()
logger = get_logger(__name__)
persona_mgr = get_persona_manager()


@router.post("/structured-extract", response_model=StructuredResponse)
@require_audit_log
async def internal_structured_extract(request: StructuredRequest) -> StructuredResponse:
    """INTERNAL: Extract structured data via LLM (ultra observable).

    Used for commands that need structured JSON responses:
    - SOAP note modifications
    - Clinical data extraction
    - Any operation requiring schema validation

    Args:
        request: Command + context + output_schema

    Returns:
        StructuredResponse with parsed JSON + observability

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

        # Call LLM - use specified provider or default from policy
        llm_response = llm_generate(
            prompt,
            provider=request.provider,
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
        parsed_response = {}

        try:
            # First, try to find JSON between ```json ... ``` or ``` ... ```
            json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # If no markdown blocks, try to find JSON between curly braces
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1

                if json_start == -1 or json_end == 0:
                    logger.warning(
                        "INTERNAL_LLM_STRUCTURED_NO_JSON_IN_RESPONSE",
                        response_text=response_text[:500],
                    )
                    parsed_response = {}
                else:
                    json_str = response_text[json_start:json_end]

                    try:
                        parsed_response = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Clean the string more aggressively
                        cleaned_json_str = json_str.strip()
                        last_brace = cleaned_json_str.rfind("}") + 1
                        if last_brace != 0:
                            cleaned_json_str = cleaned_json_str[:last_brace]

                        try:
                            parsed_response = json.loads(cleaned_json_str)
                        except json.JSONDecodeError as e2:
                            logger.warning(
                                "INTERNAL_LLM_STRUCTURED_JSON_INVALID",
                                json_str=cleaned_json_str[:500],
                                error=str(e2),
                            )
                            parsed_response = {}
        except Exception as e:
            logger.warning(
                "INTERNAL_LLM_STRUCTURED_PARSING_ERROR",
                error=str(e),
                response_text=response_text[:500],
            )
            parsed_response = {}

        # Validate response structure and ensure required fields
        if "data" not in parsed_response:
            logger.warning(
                "INTERNAL_LLM_STRUCTURED_MISSING_DATA",
                keys=list(parsed_response.keys()),
                original_response=response_text[:200],
            )
            parsed_response["data"] = {}
            for key, _description in request.output_schema.items():
                if key in parsed_response:
                    parsed_response["data"][key] = parsed_response[key]
                else:
                    parsed_response["data"][key] = f"Could not extract {key} from response"

        if "explanation" not in parsed_response:
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
