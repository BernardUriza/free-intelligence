"""SOAP generation worker - Medical notes extraction."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.policy.policy_loader import get_policy_loader
from backend.storage.task_repository import (
    create_order,
    get_diarization_segments,
    get_orders,
    get_task_chunks,
    save_soap_data,
    task_exists,
    update_task_metadata,
)
from backend.workers.tasks.base_worker import WorkerResult, measure_time

logger = get_logger(__name__)


@measure_time
def generate_soap_worker(
    session_id: str,
    soap_provider: str | None = None,
) -> dict[str, Any]:
    """Synchronous SOAP note generation from diarization.

    Args:
        session_id: Session identifier
        soap_provider: LLM provider (claude, ollama, openai, etc)

    Returns:
        WorkerResult with SOAP note (subjective, objective, assessment, plan)
    """
    try:
        start_time = time.time()
        logger.info(
            "SOAP_GENERATION_START",
            session_id=session_id,
            provider=soap_provider,
        )

        # Check DIARIZATION task exists (SOAP depends on diarization)
        if not task_exists(session_id, TaskType.DIARIZATION):
            raise ValueError(
                f"DIARIZATION task not found for {session_id}. Must run diarization first."
            )

        # Get provider from policy if not specified
        if not soap_provider:
            policy_loader = get_policy_loader()
            llm_config = policy_loader.get_llm_config()
            soap_provider = llm_config.get("primary_provider", "claude")

        # Get diarization segments
        segments = get_diarization_segments(session_id)
        if not segments:
            # Fallback: use transcription chunks if no diarization
            logger.warning(
                "NO_DIARIZATION_SEGMENTS_USING_TRANSCRIPTION",
                session_id=session_id,
            )
            chunks_data = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
            if not chunks_data:
                raise ValueError(f"No TRANSCRIPTION or DIARIZATION data for {session_id}")
            full_text = " ".join(chunk.get("transcript", "") for chunk in chunks_data)
        else:
            # Reconstruct full transcript from diarization segments
            full_text = "\n".join(
                f"{seg.get('speaker', 'Unknown')}: {seg.get('text', '')}" for seg in segments
            )

        # Estimate duration based on text length (empirical: ~1.5s per 100 words for LLM)
        word_count = len(full_text.split())
        estimated_duration = max(8, int(word_count / 100 * 1.5))  # Min 8 seconds

        # Update metadata: IN_PROGRESS with progress 10% (started)
        update_task_metadata(
            session_id,
            TaskType.SOAP_GENERATION,
            {
                "status": TaskStatus.IN_PROGRESS,
                "provider": soap_provider,
                "progress_percent": 10,
                "estimated_duration_seconds": estimated_duration,
                "started_at": datetime.now(UTC).isoformat(),
                "word_count": word_count,
                "text_length": len(full_text),
            },
        )
        logger.info(
            "SOAP_PROGRESS",
            session_id=session_id,
            progress=10,
            estimated_duration=estimated_duration,
        )

        # Update progress: 30% (text loaded, calling LLM)
        update_task_metadata(
            session_id,
            TaskType.SOAP_GENERATION,
            {
                "progress_percent": 30,
                "status_message": f"Calling {soap_provider} for SOAP extraction...",
            },
        )

        # Generate SOAP note using service
        # TODO: Update SOAPGenerationService to accept transcript directly
        # For now, we'll need to refactor the service or create a wrapper

        # Temporary: Create a simple SOAP extraction inline
        # This should be replaced with proper service integration
        from backend.services.soap_generation.llm_client import LLMClient

        llm_client = LLMClient(provider=soap_provider)

        # Update progress: 50% (LLM processing)
        update_task_metadata(
            session_id,
            TaskType.SOAP_GENERATION,
            {
                "progress_percent": 50,
                "status_message": "LLM processing medical transcript...",
            },
        )

        # Extract SOAP data
        soap_data = llm_client.extract_soap(full_text)

        # Update progress: 80% (processing results)
        update_task_metadata(
            session_id,
            TaskType.SOAP_GENERATION,
            {
                "progress_percent": 80,
                "status_message": "Processing SOAP note results...",
            },
        )

        result = {
            "soap_note": soap_data,
            "provider": soap_provider,
            "word_count": word_count,
            "text_length": len(full_text),
        }

        elapsed_time = time.time() - start_time

        # Save SOAP note to HDF5 using save_soap_data()
        save_soap_data(session_id, soap_data, TaskType.SOAP_GENERATION)

        # AUTO-CREATE ORDERS from SOAP.plan (medications + studies)
        orders_created = 0
        plan = soap_data.get("plan", {})

        # Get existing orders to avoid duplicates
        existing_orders = get_orders(session_id)
        existing_descriptions = {order.get("description") for order in existing_orders}

        # Create medication orders
        medications = plan.get("medications", [])
        if isinstance(medications, list):
            for med in medications:
                if isinstance(med, dict):
                    desc = f"{med.get('name', '')} {med.get('dose', '')}".strip()
                    if desc and desc not in existing_descriptions:
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
                        logger.info(
                            "ORDER_CREATED_FROM_SOAP",
                            session_id=session_id,
                            type="medication",
                            description=desc,
                        )

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
                        kw in study_lower
                        for kw in ["rayos", "radiografia", "tac", "resonancia", "rx"]
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
                        "ORDER_CREATED_FROM_SOAP",
                        session_id=session_id,
                        type=order_type,
                        description=study,
                    )

        logger.info(
            "SOAP_ORDERS_AUTO_CREATED",
            session_id=session_id,
            orders_created=orders_created,
        )

        # Update metadata with completion status
        update_task_metadata(
            session_id,
            TaskType.SOAP_GENERATION,
            {
                "status": TaskStatus.COMPLETED,
                "provider": soap_provider,
                "progress_percent": 100,
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": round(elapsed_time, 2),
                "status_message": "SOAP note generated successfully",
            },
        )

        logger.info(
            "SOAP_GENERATION_SUCCESS",
            session_id=session_id,
            duration_seconds=round(elapsed_time, 2),
            provider=soap_provider,
        )

        return WorkerResult(session_id=session_id, result=result).to_dict()

    except Exception as e:
        logger.error(
            "SOAP_GENERATION_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )

        # Update metadata with FAILED status
        try:
            update_task_metadata(
                session_id,
                TaskType.SOAP_GENERATION,
                {
                    "status": TaskStatus.FAILED,
                    "progress_percent": 0,
                    "error": str(e),
                    "failed_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as meta_error:
            logger.error(
                "FAILED_TO_UPDATE_ERROR_METADATA",
                session_id=session_id,
                error=str(meta_error),
            )

        raise
