"""Diarization Mixin - Speaker diarization segment storage.

Handles speaker diarization data:
- Save diarization segments
- Get diarization segments

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

from typing import Any

import h5py

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class DiarizationMixin:
    """Mixin for diarization operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP, _save_json_dataset).
    """

    def save_diarization_segments(
        self, session_id: str, segments: list[dict[str, Any]]
    ) -> None:
        """Save diarization segments to HDF5.

        Args:
            session_id: Session identifier
            segments: List of segment dicts with speaker, text, timestamps
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, "DIARIZATION")
                self._save_json_dataset(f, task_group, "segments", segments)

                logger.info(
                    "DIARIZATION_SEGMENTS_SAVED",
                    session_id=session_id,
                    segment_count=len(segments),
                )

        except Exception as e:
            logger.error(
                "SAVE_DIARIZATION_SEGMENTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def get_diarization_segments(self, session_id: str) -> list[dict[str, Any]]:
        """Get diarization segments from HDF5.

        Args:
            session_id: Session identifier

        Returns:
            List of segment dicts or empty list if not found
        """
        try:
            segments_path = f"{self.TASKS_GROUP}/{session_id}/DIARIZATION/segments"

            with h5py.File(self.h5_file_path, "r") as f:
                segments = self._load_json_dataset(f, segments_path)

                if segments is None:
                    logger.warning(
                        "DIARIZATION_SEGMENTS_NOT_FOUND",
                        session_id=session_id,
                    )
                    return []

                logger.debug(
                    "DIARIZATION_SEGMENTS_READ",
                    session_id=session_id,
                    segment_count=len(segments),
                )
                return segments

        except Exception as e:
            logger.error(
                "GET_DIARIZATION_SEGMENTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return []
