"""Emotion Analysis worker - Patient emotional state detection."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

import h5py
from backend.models.task_type import TaskStatus, TaskType
from backend.schemas.llm.preset_loader import get_preset_loader
from backend.utils.common.logging.logger import get_logger
from backend.container import get_container
from backend.core.infrastructure.workers.tasks.base_worker import measure_time
from pathlib import Path

# Use DI container for task repository functions
def task_exists(session_id: str, task_type):
    """Check if task exists via DI container."""
    task_repo = get_container().get_task_repository()
    task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
    return task_repo.task_exists(session_id, task_type_str)


def update_task_metadata(session_id: str, task_type, **metadata):
    """Update task metadata via DI container."""
    task_repo = get_container().get_task_repository()
    task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
    task_repo.save_task_metadata(session_id, task_type_str, metadata)


# Default corpus path
CORPUS_PATH = Path("storage/corpus.h5")

logger = get_logger(__name__)


@measure_time
def analyze_emotion_worker(
    session_id: str,
) -> dict[str, Any]:
    """Analyze patient emotional state from diarization segments.

    Args:
        session_id: Session identifier

    Returns:
        WorkerResult with emotion analysis
    """
    try:
        start_time = time.time()
        logger.info(
            "EMOTION_ANALYSIS_START",
            session_id=session_id,
        )

        # Check EMOTION_ANALYSIS task exists
        if not task_exists(session_id, TaskType.EMOTION_ANALYSIS):
            raise ValueError(
                f"EMOTION_ANALYSIS task not found for {session_id}. Must create first."
            )

        # Load emotion_analyzer preset
        try:
            preset_loader = get_preset_loader()
            preset = preset_loader.load_preset("emotion_analyzer")
            logger.info(
                "EMOTION_PRESET_LOADED",
                preset_id=preset.preset_id,
                version=preset.version,
                temperature=preset.temperature,
            )
        except Exception as e:
            logger.error(
                "EMOTION_PRESET_LOAD_FAILED",
                error=str(e),
            )
            raise ValueError(f"Failed to load emotion_analyzer preset: {e}") from e

        # Get diarization segments (patient speech only)
        try:
            with h5py.File(CORPUS_PATH, "r") as f:
                diarization_path = f"/sessions/{session_id}/tasks/DIARIZATION/segments"
                if diarization_path not in f:
                    raise ValueError(f"No diarization segments found for {session_id}")

                segments_data = f[diarization_path][()]
                segments_json = bytes(segments_data).decode("utf-8")
                all_segments = json.loads(segments_json)
                logger.info(
                    "DIARIZATION_SEGMENTS_LOADED",
                    session_id=session_id,
                    total_segments=len(all_segments),
                )
        except Exception as e:
            logger.error(
                "DIARIZATION_LOAD_FAILED",
                session_id=session_id,
                error=str(e),
            )
            raise ValueError(f"Failed to load diarization data: {e}") from e

        # Filter patient segments only
        patient_segments = [
            seg for seg in all_segments if seg.get("speaker", "").upper() in ["PATIENT", "PACIENTE"]
        ]
        logger.info(
            "PATIENT_SEGMENTS_FILTERED",
            session_id=session_id,
            patient_segments=len(patient_segments),
            total_segments=len(all_segments),
        )

        if not patient_segments:
            logger.warning(
                "NO_PATIENT_SEGMENTS",
                session_id=session_id,
                hint="Diarization may have failed or no patient speech detected",
            )
            # Return neutral emotion
            result = {
                "primary_emotion": "NEUTRAL",
                "confidence": 0.5,
                "detected_emotions": [],
                "red_flags": [],
                "clinical_recommendations": ["Unable to analyze - no patient speech detected"],
                "metadata": {
                    "session_id": session_id,
                    "analyzed_at": datetime.now(UTC).isoformat(),
                    "analysis_limitations": ["No patient segments found in diarization"],
                },
            }
            # Save to HDF5
            _save_emotion_result(session_id, result)
            update_task_metadata(
                session_id,
                TaskType.EMOTION_ANALYSIS,
                {
                    "status": TaskStatus.COMPLETED,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": round(time.time() - start_time, 2),
                },
            )
            return result

        # Concatenate patient speech for analysis
        patient_text = " ".join(
            seg.get("improved_text") or seg.get("text", "") for seg in patient_segments
        )
        logger.info(
            "PATIENT_TEXT_CONCATENATED",
            session_id=session_id,
            text_length=len(patient_text),
            word_count=len(patient_text.split()),
        )

        # Update metadata: IN_PROGRESS
        update_task_metadata(
            session_id,
            TaskType.EMOTION_ANALYSIS,
            {
                "status": TaskStatus.IN_PROGRESS,
                "progress_percent": 30,
                "started_at": datetime.now(UTC).isoformat(),
                "patient_segments": len(patient_segments),
            },
        )

        # Call LLM for emotion analysis using preset
        try:
            from backend.providers.llm import llm_generate

            # Build prompt: system prompt + patient text + few-shot examples
            prompt_parts = [preset.system_prompt]

            # Add few-shot examples if available
            if preset.examples:
                prompt_parts.append("\n\n## Examples:")
                for example in preset.examples[:2]:  # Limit to 2 examples to save tokens
                    prompt_parts.append(f"\nInput: {example.get('input', '')}")
                    prompt_parts.append(
                        f"Output: {json.dumps(example.get('output', {}), ensure_ascii=False)}"
                    )

            # Add actual patient text
            prompt_parts.append(f"\n\n## Patient Speech to Analyze:\n{patient_text}")

            full_prompt = "\n".join(prompt_parts)

            logger.info(
                "EMOTION_LLM_CALL_START",
                session_id=session_id,
                provider=preset.provider,
                model=preset.model,
                prompt_length=len(full_prompt),
                patient_text_length=len(patient_text),
            )

            # Call LLM with preset configuration
            llm_response = llm_generate(
                full_prompt,
                provider=preset.provider,
                temperature=preset.temperature,
                max_tokens=preset.max_tokens,
            )

            logger.info(
                "EMOTION_LLM_CALL_COMPLETE",
                session_id=session_id,
                response_length=len(llm_response.content),
            )

            # Parse JSON response
            try:
                result = json.loads(llm_response.content)
            except json.JSONDecodeError as e:
                logger.error(
                    "EMOTION_LLM_JSON_PARSE_FAILED",
                    session_id=session_id,
                    error=str(e),
                    response_preview=llm_response.content[:200],
                )
                # Fallback: try to extract JSON from markdown code blocks
                import re

                json_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", llm_response.content, re.DOTALL
                )
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    raise ValueError(
                        f"LLM response is not valid JSON: {llm_response.content[:200]}"
                    ) from e

            # Validate result structure (basic validation)
            required_fields = ["primary_emotion", "confidence", "detected_emotions"]
            for field in required_fields:
                if field not in result:
                    logger.warning(
                        "EMOTION_RESULT_MISSING_FIELD",
                        session_id=session_id,
                        missing_field=field,
                    )
                    # Set defaults
                    if field == "primary_emotion":
                        result["primary_emotion"] = "NEUTRAL"
                    elif field == "confidence":
                        result["confidence"] = 0.5
                    elif field == "detected_emotions":
                        result["detected_emotions"] = []

            # Add metadata
            result["metadata"] = {
                "session_id": session_id,
                "analyzed_at": datetime.now(UTC).isoformat(),
                "model_version": preset.version,
                "provider": preset.provider,
                "model": preset.model,
                "patient_segments_analyzed": len(patient_segments),
                "llm_response_id": getattr(llm_response, "response_id", None),
            }

            logger.info(
                "EMOTION_ANALYSIS_LLM_SUCCESS",
                session_id=session_id,
                primary_emotion=result.get("primary_emotion"),
                confidence=result.get("confidence"),
            )

        except Exception as e:
            logger.error(
                "EMOTION_LLM_CALL_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            # Fallback to neutral result if LLM fails
            logger.warning(
                "EMOTION_ANALYSIS_FALLBACK",
                session_id=session_id,
                message="LLM call failed - returning neutral emotion result",
            )
            result = {
                "primary_emotion": "NEUTRAL",
                "confidence": 0.5,
                "severity": 0,
                "detected_emotions": [],
                "red_flags": [],
                "clinical_recommendations": [
                    "Emotion analysis unavailable - LLM call failed",
                    "Manual clinical assessment recommended",
                ],
                "support_needs": [],
                "metadata": {
                    "session_id": session_id,
                    "analyzed_at": datetime.now(UTC).isoformat(),
                    "model_version": preset.version,
                    "patient_segments_analyzed": len(patient_segments),
                    "error": str(e),
                    "fallback": True,
                },
            }

        # Save result to HDF5
        _save_emotion_result(session_id, result)

        # Update metadata: COMPLETED
        update_task_metadata(
            session_id,
            TaskType.EMOTION_ANALYSIS,
            {
                "status": TaskStatus.COMPLETED,
                "progress_percent": 100,
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": round(time.time() - start_time, 2),
                "primary_emotion": result["primary_emotion"],
                "confidence": result["confidence"],
            },
        )

        logger.info(
            "EMOTION_ANALYSIS_COMPLETE",
            session_id=session_id,
            primary_emotion=result["primary_emotion"],
            confidence=result["confidence"],
            duration_seconds=round(time.time() - start_time, 2),
        )

        return result

    except Exception as e:
        logger.error(
            "EMOTION_ANALYSIS_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        # Update metadata: FAILED
        if task_exists(session_id, TaskType.EMOTION_ANALYSIS):
            update_task_metadata(
                session_id,
                TaskType.EMOTION_ANALYSIS,
                {
                    "status": TaskStatus.FAILED,
                    "error": str(e),
                    "failed_at": datetime.now(UTC).isoformat(),
                },
            )
        raise


def _save_emotion_result(session_id: str, result: dict[str, Any]) -> None:
    """Save emotion analysis result to HDF5.

    Args:
        session_id: Session identifier
        result: Emotion analysis result dictionary
    """
    try:
        result_json = json.dumps(result, ensure_ascii=False, indent=2)
        with h5py.File(CORPUS_PATH, "a") as f:
            result_path = f"/sessions/{session_id}/tasks/EMOTION_ANALYSIS/result"
            if result_path in f:
                del f[result_path]
            f.create_dataset(
                result_path,
                data=result_json.encode("utf-8"),
                dtype=h5py.special_dtype(vlen=bytes),
            )
        logger.info(
            "EMOTION_RESULT_SAVED",
            session_id=session_id,
            path=result_path,
        )
    except Exception as e:
        logger.error(
            "EMOTION_RESULT_SAVE_FAILED",
            session_id=session_id,
            error=str(e),
        )
        raise
