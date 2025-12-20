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
from pydantic import BaseModel, Field, field_validator

from backend.clients import get_llm_client
from backend.logger import get_logger
from backend.src.fi_soap_generation.services.soap_models import SOAPNote
from backend.validators import validate_session_id

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class SOAPUpdateRequest(BaseModel):
    """Request body for SOAP update."""

    soap: SOAPNote = Field(..., description="Complete validated SOAP data structure")

    @field_validator("soap", mode="before")
    @classmethod
    def validate_soap_structure(cls, v: Any) -> dict:
        """Validate SOAP structure before creating the model."""
        if isinstance(v, dict):
            # Check if required sections exist
            required_sections = ["subjective", "objective", "assessment", "plan"]
            for section in required_sections:
                if section not in v:
                    raise ValueError(f"Missing required section: {section}")

            # Create and validate the SOAPNote instance
            try:
                soap_note = SOAPNote.model_validate(v)
                validation_errors = soap_note.validate_completeness()
                if validation_errors:
                    raise ValueError(f"SOAP note validation failed: {'; '.join(validation_errors)}")
                return soap_note
            except Exception as e:
                raise ValueError(f"Invalid SOAP structure: {e!s}")
        return v


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

    updates: dict[str, str | dict] = Field(
        ...,
        description="Dictionary of SOAP field updates (field_name: operation:content or complex object)",
    )
    explanation: str = Field(..., description="Human-readable explanation of changes")
    success: bool = Field(default=True, description="Whether operation succeeded")


# ============================================================================
# SOAP CRUD Endpoints
# ============================================================================


# P0 FIX: validate_session_id removed - now uses shared backend.validators.validate_session_id


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
        400: Invalid session_id
        500: Failed to load or generate SOAP data
    """
    # Validate session ID first
    validate_session_id(session_id)

    from backend.src.fi_storage.infrastructure.hdf5.task_repository import get_soap_data

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
            from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
                ensure_task_exists,
            )
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

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
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
        400: Invalid session_id or SOAP data
        500: Failed to save SOAP data
    """
    # Validate session ID first
    validate_session_id(session_id)

    from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
        create_order,
        get_orders,
        save_soap_data,
    )

    try:
        logger.info("SOAP_UPDATE_STARTED", session_id=session_id)

        # Validate SOAP data structure before saving
        validation_errors = request.soap.validate_completeness()
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid SOAP data: {'; '.join(validation_errors)}",
            )

        # Save SOAP data
        soap_path = save_soap_data(session_id, request.soap)

        # TRIGGER: Create orders from SOAP.plan
        orders_created = 0
        plan = request.soap.plan

        # Get existing orders to avoid duplicates
        existing_orders = get_orders(session_id)
        existing_descriptions = {order.get("description") for order in existing_orders}

        # Create medication orders
        medications = plan.treatment
        if medications:
            # Extract medications from treatment plan
            # This is a simplified approach - in a real system,
            # this would need more sophisticated parsing
            med_desc = f"{plan.treatment[:50]}..." if len(plan.treatment) > 50 else plan.treatment
            if med_desc.strip() and med_desc not in existing_descriptions:
                create_order(
                    session_id,
                    {
                        "type": "medication",
                        "description": med_desc,
                        "details": plan.follow_up,
                        "source": "soap",
                    },
                )
                orders_created += 1

        # Create lab/imaging orders
        studies = plan.studies
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

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
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
    # Validate session ID first
    validate_session_id(session_id)

    # Validate request command length
    if not request.command or len(request.command.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command cannot be empty",
        )

    if len(request.command) > 1000:  # Reasonable limit for a command
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command too long: maximum 1000 characters allowed",
        )

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
