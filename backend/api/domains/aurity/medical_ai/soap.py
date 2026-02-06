"""SOAP Notes Workflow Endpoints - CRUD + Natural Language Assistant.

PUBLIC layer endpoints for SOAP notes management:
- GET /soap/sessions/{session_id} - Get SOAP note data
- PUT /soap/sessions/{session_id} - Update SOAP note (triggers order creation)
- POST /soap/sessions/{session_id}/assistant - Natural language SOAP modification

Architecture:
  PUBLIC (this file) -> REPOSITORY -> HDF5

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration from routers/soap/soap.py)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.clients.dependencies import get_llm_client_dep
from backend.infrastructure.auth import User, get_current_user, validate_session_access
from backend.repositories.interfaces import ITaskRepository
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id

from .soap_models import AssistantRequest, AssistantResponse, SOAPUpdateRequest

if TYPE_CHECKING:
    from backend.clients.internal_llm_client import InternalLLMClient

logger = get_logger(__name__)

router = APIRouter(prefix="/soap", tags=["SOAP"])


# ============================================================================
# SOAP CRUD Endpoints
# ============================================================================


@router.get(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
)
async def get_soap_workflow(
    session_id: str,
    task_repo: ITaskRepository = Depends(get_task_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get SOAP note data - generates if not exists (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        task_repo: Task repository (injected via Depends)

    Returns:
        SOAP data with subjective, objective, assessment, plan

    Raises:
        400: Invalid session_id
        500: Failed to load or generate SOAP data
    """
    # Validate session ID format and ownership
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="view SOAP notes")

    try:
        logger.info("SOAP_GET_STARTED", session_id=session_id)

        # Try to get existing SOAP data
        try:
            soap_data = task_repo.get_soap_data(session_id)
            logger.info("SOAP_GET_SUCCESS", session_id=session_id)
            return {
                "session_id": session_id,
                "soap_note": soap_data,
            }
        except ValueError:
            # SOAP doesn't exist - generate it using service layer
            logger.info("SOAP_NOT_FOUND_GENERATING", session_id=session_id)

            from backend.models.task_type import TaskType
            from backend.infrastructure.workers.tasks.soap_worker import generate_soap_worker

            # Ensure SOAP_GENERATION task exists before calling worker
            task_repo.ensure_task_exists(session_id, TaskType.SOAP_GENERATION.value, allow_existing=True)

            # Call worker synchronously (service layer) - DI injected
            generate_soap_worker(session_id, task_repo=task_repo)

            # Get generated SOAP
            soap_data = task_repo.get_soap_data(session_id)

            logger.info("SOAP_GENERATED_SUCCESS", session_id=session_id)

            return {
                "session_id": session_id,
                "soap_note": soap_data,
            }

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="soap_retrieved",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get SOAP data: {e!s}",
        ) from e


@router.put(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
)
async def update_soap_workflow(
    session_id: str,
    request: SOAPUpdateRequest,
    task_repo: ITaskRepository = Depends(get_task_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update SOAP note data (PUBLIC endpoint).

    Saves SOAP data and triggers ORDER creation if medications/studies added.

    Args:
        session_id: Session UUID
        request: SOAP data to save
        task_repo: Task repository (injected via Depends)

    Returns:
        Success message with version info

    Raises:
        400: Invalid session_id or SOAP data
        500: Failed to save SOAP data
    """
    # Validate session ID format and ownership
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="update SOAP notes")

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
        soap_path = task_repo.save_soap_data(session_id, request.soap)

        # TRIGGER: Create orders from SOAP.plan
        orders_created = 0
        plan = request.soap.plan

        # Get existing orders to avoid duplicates
        existing_orders = task_repo.get_orders(session_id)
        existing_descriptions = {order.get("description") for order in existing_orders}

        # Create medication orders
        medications = plan.treatment
        if medications:
            med_desc = f"{plan.treatment[:50]}..." if len(plan.treatment) > 50 else plan.treatment
            if med_desc.strip() and med_desc not in existing_descriptions:
                task_repo.create_order(
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

                    task_repo.create_order(
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
        raise
    except Exception as e:
        audit_service.log_action(
            action="soap_updated",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
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
    llm_client: "InternalLLMClient" = Depends(get_llm_client_dep),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
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
    # Validate session ID format and ownership
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="use SOAP assistant")

    # Validate request command length
    if not request.command or len(request.command.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command cannot be empty",
        )

    if len(request.command) > 1000:
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
                        "hpi": "append:\\n\\n* Diabetes mellitus (antecedente no mencionado en consulta actual)",
                    },
                    "explanation": "He agregado diabetes mellitus al historial medico pasado y como nota en el historial de enfermedad actual.",
                },
                {
                    "command": "agregar alergia a penicilina",
                    "updates": {"allergies": "add_item:Penicilina"},
                    "explanation": "He agregado penicilina a la lista de alergias conocidas.",
                },
                {
                    "command": "receta sertralina 50mg al dia para depresion",
                    "updates": {
                        "medications": 'add_item:{"name": "Sertralina", "dosage": "50mg", "frequency": "1 vez al dia"}',
                        "pastMedicalHistory": "add_item:Depresion",
                        "hpi": "append:\\n\\n* Depresion (se inicia tratamiento farmacologico)",
                    },
                    "explanation": "He agregado sertralina 50mg al dia a los medicamentos recetados, depresion al historial medico pasado, y una nota en HPI.",
                },
            ],
        }

        # Define expected output schema
        output_schema = {
            "updates": "dict[str, str] - Dictionary of SOAP field updates (field_name: operation:content)",
            "explanation": "str - Human-readable explanation of changes made",
        }

        # Call internal LLM endpoint via HTTP client
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
        audit_service.log_action(
            action="soap_assistant_command",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={
                "error": str(e),
                "error_type": type(e).__name__,
                "command": request.command[:100],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process assistant command: {e!s}",
        ) from e
