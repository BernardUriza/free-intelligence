"""SOAP Notes Workflow Endpoints - CRUD + Natural Language Assistant.

PUBLIC layer endpoints for SOAP notes management:
- GET /sessions/{session_id}/soap → Get SOAP note data
- PUT /sessions/{session_id}/soap → Update SOAP note (triggers order creation)
- POST /sessions/{session_id}/assistant → Natural language SOAP modification

Architecture:
  PUBLIC (this file) → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-15 (Refactored from monolithic router)
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.providers.llm import llm_generate

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class SOAPUpdateRequest(BaseModel):
    """Request body for SOAP update."""

    soap: dict[str, Any] = Field(..., description="Complete SOAP data structure")


class AssistantRequest(BaseModel):
    """Request body for SOAP assistant natural language commands."""

    command: str = Field(
        ...,
        min_length=1,
        description="Natural language command to modify SOAP data",
        examples=["agrega que la paciente tiene diabetes", "nota: paciente vive con VIH"],
    )
    current_soap: dict[str, Any] = Field(
        ..., description="Current SOAP data structure to be modified"
    )


class AssistantResponse(BaseModel):
    """Response from SOAP assistant with structured updates."""

    updates: dict[str, str] = Field(
        ...,
        description="Dictionary of SOAP field updates (field_name: operation:content)",
    )
    explanation: str = Field(..., description="Human-readable explanation of changes")
    success: bool = Field(default=True, description="Whether operation succeeded")


# ============================================================================
# SOAP CRUD Endpoints
# ============================================================================


@router.get(
    "/sessions/{session_id}/soap",
    status_code=status.HTTP_200_OK,
)
async def get_soap_workflow(session_id: str) -> dict:
    """Get SOAP note data - generates if not exists (PUBLIC endpoint).

    Args:
        session_id: Session UUID

    Returns:
        SOAP data with subjective, objective, assessment, plan

    Raises:
        500: Failed to load or generate SOAP data
    """
    from backend.storage.task_repository import get_soap_data

    try:
        logger.info("SOAP_GET_STARTED", session_id=session_id)

        # Try to get existing SOAP data
        try:
            soap_data = get_soap_data(session_id)
            logger.info("SOAP_GET_SUCCESS", session_id=session_id)
            return {
                "session_id": session_id,
                "soap_note": soap_data,
            }
        except ValueError:
            # SOAP doesn't exist - generate it using service layer
            logger.info("SOAP_NOT_FOUND_GENERATING", session_id=session_id)

            from backend.models.task_type import TaskType
            from backend.storage.task_repository import ensure_task_exists
            from backend.workers.tasks.soap_worker import generate_soap_worker

            # Ensure SOAP_GENERATION task exists before calling worker
            ensure_task_exists(session_id, TaskType.SOAP_GENERATION, allow_existing=True)

            # Call worker synchronously (service layer)
            generate_soap_worker(session_id)

            # Get generated SOAP
            soap_data = get_soap_data(session_id)

            logger.info("SOAP_GENERATED_SUCCESS", session_id=session_id)

            return {
                "session_id": session_id,
                "soap_note": soap_data,
            }

    except Exception as e:
        logger.error(
            "SOAP_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SOAP data: {e!s}",
        ) from e


@router.put(
    "/sessions/{session_id}/soap",
    status_code=status.HTTP_200_OK,
)
async def update_soap_workflow(
    session_id: str,
    request: SOAPUpdateRequest,
) -> dict:
    """Update SOAP note data (PUBLIC endpoint).

    Saves SOAP data and triggers ORDER creation if medications/studies added.

    Args:
        session_id: Session UUID
        request: SOAP data to save

    Returns:
        Success message with version info

    Raises:
        400: Invalid SOAP data
        500: Failed to save SOAP data
    """
    from backend.storage.task_repository import create_order, get_orders, save_soap_data

    try:
        logger.info("SOAP_UPDATE_STARTED", session_id=session_id)

        # Save SOAP data
        soap_path = save_soap_data(session_id, request.soap)

        # TRIGGER: Create orders from SOAP.plan
        orders_created = 0
        plan = request.soap.get("plan", {})

        # Get existing orders to avoid duplicates
        existing_orders = get_orders(session_id)
        existing_descriptions = {order.get("description") for order in existing_orders}

        # Create medication orders
        medications = plan.get("medications", [])
        if isinstance(medications, list):
            for med in medications:
                if isinstance(med, dict):
                    desc = f"{med.get('name', '')} {med.get('dose', '')}"
                    if desc.strip() and desc not in existing_descriptions:
                        create_order(
                            session_id,
                            {
                                "type": "medication",
                                "description": desc,
                                "details": f"{med.get('frequency', '')} - {med.get('duration', '')}",
                                "source": "soap",
                            },
                        )
                        orders_created += 1

        # Create lab/imaging orders
        studies = plan.get("studies", [])
        if isinstance(studies, list):
            for study in studies:
                if isinstance(study, str) and study not in existing_descriptions:
                    # Determine type based on keywords
                    study_lower = study.lower()
                    if any(
                        kw in study_lower
                        for kw in ["biometria", "quimica", "sangre", "laboratorio"]
                    ):
                        order_type = "lab"
                    elif any(
                        kw in study_lower for kw in ["rayos", "radiografia", "tac", "resonancia"]
                    ):
                        order_type = "imaging"
                    else:
                        order_type = "lab"

                    create_order(
                        session_id,
                        {
                            "type": order_type,
                            "description": study,
                            "details": "",
                            "source": "soap",
                        },
                    )
                    orders_created += 1

        logger.info(
            "SOAP_UPDATE_SUCCESS",
            session_id=session_id,
            soap_path=soap_path,
            orders_created=orders_created,
        )

        return {
            "success": True,
            "session_id": session_id,
            "soap_path": soap_path,
            "orders_created": orders_created,
        }

    except Exception as e:
        logger.error(
            "SOAP_UPDATE_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update SOAP data: {e!s}",
        ) from e


# ============================================================================
# SOAP Assistant - Natural Language Modification
# ============================================================================


@router.post(
    "/sessions/{session_id}/assistant",
    status_code=status.HTTP_200_OK,
    response_model=AssistantResponse,
)
async def soap_assistant_workflow(
    session_id: str,
    request: AssistantRequest,
) -> AssistantResponse:
    """Process natural language command to modify SOAP data (PUBLIC orchestrator).

    Uses LLM to parse natural language commands and return structured SOAP updates.
    Supports commands like:
    - "agrega que la paciente tiene diabetes"
    - "nota: la paciente vive con VIH"
    - "agregar alergia a penicilina"

    Args:
        session_id: Session UUID (for audit logging)
        request: Command and current SOAP data

    Returns:
        Structured updates to SOAP data with explanation

    Raises:
        400: Invalid command or SOAP data
        500: LLM processing failed
    """
    response_text = ""  # Initialize to avoid unbound error in exception handlers
    try:
        logger.info(
            "ASSISTANT_COMMAND_START",
            session_id=session_id,
            command=request.command,
        )

        # Build prompt for LLM
        prompt = f"""You are a medical SOAP notes assistant. Parse the user's natural language command and return structured updates to the SOAP data.

Current SOAP data:
{request.current_soap}

User command: "{request.command}"

Your task:
1. Understand what medical information the user wants to add/modify
2. Determine which SOAP section(s) should be updated
3. Return structured updates in JSON format

SOAP sections available:
- hpi: History of Present Illness (narrative)
- pastMedicalHistory: Past medical conditions (array of strings)
- allergies: Known allergies (array of strings)
- medications: Current medications (array of objects with fields: name, dosage, frequency)
- diagnosticTests: Lab/imaging orders (array of strings like "Biometría Hemática Completa", "Radiografía de Tórax")
- physicalExam: Physical examination findings
- primaryDiagnosis: Main diagnosis (object with code and description)
- differentialDiagnoses: Alternative diagnoses (array)
- followUp: Follow-up instructions

Operations:
- "append:text" - Add text to existing content
- "replace:text" - Replace entire content
- "add_item:text" - Add single item to array
- "add_items:[item1,item2,...]" - Add multiple items to array (for strings, use JSON array; for objects, use array of JSON objects)

Examples:

Command: "agrega que la paciente tiene diabetes"
Response:
{{
  "updates": {{
    "pastMedicalHistory": "add_item:Diabetes mellitus",
    "hpi": "append:\\n\\n• Diabetes mellitus (antecedente no mencionado en consulta actual)"
  }},
  "explanation": "He agregado diabetes mellitus al historial médico pasado y como nota en el historial de enfermedad actual."
}}

Command: "agregar alergia a penicilina"
Response:
{{
  "updates": {{
    "allergies": "add_item:Penicilina"
  }},
  "explanation": "He agregado penicilina a la lista de alergias conocidas."
}}

Command: "receta sertralina 50mg al día para depresión"
Response:
{{
  "updates": {{
    "medications": "add_item:{{\\"name\\": \\"Sertralina\\", \\"dosage\\": \\"50mg\\", \\"frequency\\": \\"1 vez al día\\"}}",
    "pastMedicalHistory": "add_item:Depresión",
    "hpi": "append:\\n\\n• Depresión (se inicia tratamiento farmacológico)"
  }},
  "explanation": "He agregado sertralina 50mg al día a los medicamentos recetados, depresión al historial médico pasado, y una nota en HPI."
}}

Command: "agrega hipertensión, diabetes tipo 2 y receta losartán 50mg c/12h y metformina 850mg c/8h"
Response:
{{
  "updates": {{
    "pastMedicalHistory": "add_items:[\\"Hipertensión arterial\\",\\"Diabetes mellitus tipo 2\\"]",
    "medications": "add_items:[{{\\"name\\":\\"Losartán\\",\\"dosage\\":\\"50mg\\",\\"frequency\\":\\"cada 12 horas\\"}},{{\\"name\\":\\"Metformina\\",\\"dosage\\":\\"850mg\\",\\"frequency\\":\\"cada 8 horas\\"}}]",
    "hpi": "append:\\n\\n• Hipertensión arterial y Diabetes tipo 2 (se inicia tratamiento)"
  }},
  "explanation": "He agregado hipertensión arterial y diabetes tipo 2 al historial médico, y dos medicamentos (losartán y metformina)."
}}

Command: "solicita biometría hemática completa, química sanguínea y radiografía de tórax"
Response:
{{
  "updates": {{
    "diagnosticTests": "add_items:[\\"Biometría Hemática Completa\\",\\"Química Sanguínea\\",\\"Radiografía de Tórax\\"]"
  }},
  "explanation": "He agregado tres órdenes médicas: biometría hemática completa, química sanguínea y radiografía de tórax."
}}

Now process this command and respond ONLY with valid JSON (no markdown, no explanations outside JSON):
"""

        # Call LLM
        logger.info("ASSISTANT_LLM_CALL")
        response = llm_generate(
            prompt,
            max_tokens=2048,
            temperature=0.3,
        )

        response_text = response.content.strip()

        logger.debug(
            "ASSISTANT_LLM_RESPONSE",
            response_length=len(response_text),
            response_preview=response_text[:200],
        )

        # Parse JSON response
        # Extract JSON from response (handle markdown code blocks)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in LLM response")

        json_str = response_text[json_start:json_end]
        parsed_response = json.loads(json_str)

        # Validate response structure
        if "updates" not in parsed_response or "explanation" not in parsed_response:
            raise ValueError("Invalid response structure from LLM")

        logger.info(
            "ASSISTANT_COMMAND_SUCCESS",
            session_id=session_id,
            num_updates=len(parsed_response["updates"]),
        )

        return AssistantResponse(
            updates=parsed_response["updates"],
            explanation=parsed_response["explanation"],
            success=True,
        )

    except json.JSONDecodeError as e:
        logger.error(
            "ASSISTANT_JSON_PARSE_ERROR",
            session_id=session_id,
            error=str(e),
            response_text=response_text[:500] if response_text else "N/A",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse LLM response as JSON: {e!s}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "ASSISTANT_COMMAND_FAILED",
            session_id=session_id,
            command=request.command,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process assistant command: {e!s}",
        ) from e
