"""SOAP Mixin - Clinical SOAP note storage.

Handles SOAP note data:
- Save SOAP notes
- Get SOAP notes

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

from typing import Any

import h5py

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class SOAPMixin:
    """Mixin for SOAP note operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP, _save_json_dataset).
    """

    def get_soap_data(self, session_id: str) -> dict[str, Any] | None:
        """Get SOAP note from HDF5.

        Args:
            session_id: Session identifier

        Returns:
            SOAP note dict or None if not found
        """
        try:
            soap_dataset_path = f"{self.TASKS_GROUP}/{session_id}/SOAP_GENERATION/soap_note"

            with h5py.File(self.h5_file_path, "r") as f:
                return self._load_json_dataset(f, soap_dataset_path)

        except Exception as e:
            logger.error(
                "GET_SOAP_DATA_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return None

    def save_soap_data(
        self, session_id: str, soap_data: dict[str, Any], task_type: str = "SOAP_GENERATION"
    ) -> None:
        """Save SOAP note to HDF5.

        Args:
            session_id: Session identifier
            soap_data: SOAP note dict (subjective, objective, assessment, plan)
            task_type: Task type (default: SOAP_GENERATION)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)
                self._save_json_dataset(f, task_group, "soap_note", soap_data)

                logger.info(
                    "SOAP_NOTE_SAVED",
                    session_id=session_id,
                )

        except Exception as e:
            logger.error(
                "SAVE_SOAP_DATA_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise
