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

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.clients import get_llm_client
from backend.logger import get_logger

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

    REFACTORED: Now uses InternalLLMClient → /internal/llm/structured-extract
    for ultra observability of all LLM interactions.

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
    try:
        logger.info(
            "ASSISTANT_COMMAND_START",
            session_id=session_id,
            command=request.command,
        )

        # Build context with current SOAP + instruction examples
        context = {
            "current_soap": request.current_soap,
            "soap_sections": {
                "hpi": "History of Present Illness (narrative)",
                "pastMedicalHistory": "Past medical conditions (array of strings)",
                "allergies": "Known allergies (array of strings)",
                "medications": "Current medications (array of objects: name, dosage, frequency)",
                "diagnosticTests": "Lab/imaging orders (array of strings)",
                "physicalExam": "Physical examination findings",
                "primaryDiagnosis": "Main diagnosis (object with code and description)",
                "differentialDiagnoses": "Alternative diagnoses (array)",
                "followUp": "Follow-up instructions",
            },
            "operations": {
                "append": "Add text to existing content",
                "replace": "Replace entire content",
                "add_item": "Add single item to array",
                "add_items": "Add multiple items to array (JSON array format)",
            },
            "examples": [
                {
                    "command": "agrega que la paciente tiene diabetes",
                    "updates": {
                        "pastMedicalHistory": "add_item:Diabetes mellitus",
                        "hpi": "append:\\n\\n• Diabetes mellitus (antecedente no mencionado en consulta actual)",
                    },
                    "explanation": "He agregado diabetes mellitus al historial médico pasado y como nota en el historial de enfermedad actual.",
                },
                {
                    "command": "agregar alergia a penicilina",
                    "updates": {"allergies": "add_item:Penicilina"},
                    "explanation": "He agregado penicilina a la lista de alergias conocidas.",
                },
                {
                    "command": "receta sertralina 50mg al día para depresión",
                    "updates": {
                        "medications": 'add_item:{"name": "Sertralina", "dosage": "50mg", "frequency": "1 vez al día"}',
                        "pastMedicalHistory": "add_item:Depresión",
                        "hpi": "append:\\n\\n• Depresión (se inicia tratamiento farmacológico)",
                    },
                    "explanation": "He agregado sertralina 50mg al día a los medicamentos recetados, depresión al historial médico pasado, y una nota en HPI.",
                },
            ],
        }

        # Define expected output schema
        output_schema = {
            "updates": "dict[str, str] - Dictionary of SOAP field updates (field_name: operation:content)",
            "explanation": "str - Human-readable explanation of changes made",
        }

        # Call internal LLM endpoint via HTTP client (ultra observable)
        llm_client = get_llm_client()

        result = await llm_client.structured_extract(
            persona="soap_editor",
            command=request.command,
            context=context,
            output_schema=output_schema,
            session_id=session_id,
        )

        # Extract data from structured response
        updates = result["data"].get("updates", {})
        explanation = result["data"].get("explanation", "Updates applied successfully")

        logger.info(
            "ASSISTANT_COMMAND_SUCCESS",
            session_id=session_id,
            num_updates=len(updates),
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
        )

        return AssistantResponse(
            updates=updates,
            explanation=explanation,
            success=True,
        )

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
