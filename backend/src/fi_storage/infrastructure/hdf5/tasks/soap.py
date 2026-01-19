"""SOAP note storage operations for HDF5.

Provides CRUD operations for SOAP notes (Subjective, Objective, Assessment, Plan)
within session-level HDF5 files. SOAP notes are the primary clinical documentation
output from medical consultations.

Storage schema:
  /sessions/{session_id}/tasks/SOAP_GENERATION/
    ├── soap_data              # Current SOAP note (JSON encoded)
    └── version_history/       # Audit trail of all versions
        ├── v_YYYYMMDD_HHMMSS
        └── ...

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.models.task_type import TaskType
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
    CORPUS_PATH,
    get_session_h5_path,
)
from backend.src.fi_storage.infrastructure.hdf5.session_locks import locked_session_h5
from backend.src.fi_storage.infrastructure.hdf5.tasks.h5_file_access import (
    open_h5_read,
)

__all__ = [
    "save_soap_data",
    "get_soap_data",
]

logger = get_logger(__name__)


def save_soap_data(
    session_id: str,
    soap_data: dict[str, Any],
    task_type: TaskType = TaskType.SOAP_GENERATION,
) -> str:
    """Save SOAP data to HDF5.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

    WARNING: Contains del operation violating append-only pattern.

    Args:
        session_id: Session identifier
        soap_data: SOAP note data (subjective, objective, assessment, plan)
        task_type: Task type (default SOAP_GENERATION)

    Returns:
        HDF5 path to SOAP data
    """
    session_file = get_session_h5_path(session_id)
    session_file.parent.mkdir(parents=True, exist_ok=True)

    with locked_session_h5(session_id, mode="a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        # Create task if doesn't exist
        if task_path not in f:  # type: ignore[operator]
            f.create_group(task_path)  # type: ignore[union-attr]

        task_group = f[task_path]  # type: ignore[index]

        # Save SOAP data as JSON
        soap_json = json.dumps(soap_data)

        # Delete existing if present (VIOLATION: append-only)
        if "soap_data" in task_group:  # type: ignore[operator]
            # Log deletion for audit trail (HIPAA compliance)
            old_data = task_group["soap_data"][()]  # type: ignore[index]
            old_value = old_data.decode("utf-8", errors="ignore") if isinstance(old_data, bytes) else str(old_data)
            logger.warning(
                "DATASET_DELETED",
                session_id=session_id,
                path=f"{task_path}/soap_data",
                old_value_size=len(old_value),
                old_value_preview=old_value[:100],
                reason="soap_regeneration",
                timestamp=datetime.now(UTC).isoformat(),
            )
            del task_group["soap_data"]  # type: ignore[index]

        task_group.create_dataset(  # type: ignore[union-attr]
            "soap_data", data=soap_json.encode("utf-8")
        )

        # Save version to history (audit trail)
        if "version_history" not in task_group:  # type: ignore[operator]
            task_group.create_group("version_history")  # type: ignore[union-attr]

        history_group = task_group["version_history"]  # type: ignore[index]
        version_key = f"v_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        history_group.create_dataset(  # type: ignore[union-attr]
            version_key, data=soap_json.encode("utf-8")
        )

        logger.info(
            "SOAP_DATA_SAVED",
            session_id=session_id,
            task_type=task_type.value,
            version=version_key,
        )

    return f"{task_path}/soap_data"


def get_soap_data(
    session_id: str,
    task_type: TaskType = TaskType.SOAP_GENERATION,
) -> dict[str, Any]:
    """Get SOAP data from HDF5.

    Args:
        session_id: Session identifier
        task_type: Task type (default SOAP_GENERATION)

    Returns:
        SOAP data dictionary

    Raises:
        ValueError: If task or SOAP data not found
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with open_h5_read() as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} not found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Try new format first, then fall back to legacy format
        if "soap_data" in task_group:  # type: ignore[operator]
            soap_json = task_group["soap_data"][()].decode("utf-8")  # type: ignore[index]
        elif "soap_note" in task_group:  # type: ignore[operator]
            # Legacy format compatibility
            soap_json = task_group["soap_note"][()].decode("utf-8")  # type: ignore[index]
        else:
            raise ValueError(f"No SOAP data found for session {session_id}")

        soap_data = json.loads(soap_json)

    logger.info(
        "SOAP_DATA_LOADED",
        session_id=session_id,
        task_type=task_type.value,
    )

    return soap_data
