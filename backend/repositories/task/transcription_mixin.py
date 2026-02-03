"""Transcription Mixin - Transcription and audio storage.

Handles transcription data:
- WebSpeech transcripts
- Full transcription text
- Full audio storage

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

import h5py

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class TranscriptionMixin:
    """Mixin for transcription and audio operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP, _ensure_task_group).
    """

    def add_webspeech_transcripts(
        self, session_id: str, transcripts: list[str], task_type: str = "TRANSCRIPTION"
    ) -> None:
        """Save webspeech transcripts to HDF5.

        Args:
            session_id: Session identifier
            transcripts: List of transcript strings from WebSpeech
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)
                self._save_json_dataset(f, task_group, "webspeech_final", transcripts)

                logger.info(
                    "WEBSPEECH_TRANSCRIPTS_SAVED",
                    session_id=session_id,
                    count=len(transcripts),
                )

        except Exception as e:
            logger.error(
                "ADD_WEBSPEECH_TRANSCRIPTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def add_full_transcription(
        self, session_id: str, full_text: str, task_type: str = "TRANSCRIPTION"
    ) -> None:
        """Save full concatenated transcription to HDF5.

        Args:
            session_id: Session identifier
            full_text: Full concatenated transcript text
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)

                # Delete existing full_transcription if present
                if "full_transcription" in task_group:
                    del task_group["full_transcription"]

                # Create new full_transcription dataset
                task_group.create_dataset(
                    "full_transcription",
                    data=full_text.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "FULL_TRANSCRIPTION_SAVED",
                    session_id=session_id,
                    length=len(full_text),
                )

        except Exception as e:
            logger.error(
                "ADD_FULL_TRANSCRIPTION_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def add_full_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        filename: str = "full_audio.webm",
        task_type: str = "TRANSCRIPTION",
    ) -> None:
        """Save full concatenated audio to HDF5.

        Args:
            session_id: Session identifier
            audio_bytes: Full concatenated audio bytes
            filename: Audio filename (default: full_audio.webm)
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)

                # Delete existing full audio if present
                if filename in task_group:
                    del task_group[filename]

                # Create new full audio dataset
                task_group.create_dataset(
                    filename,
                    data=audio_bytes,
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "FULL_AUDIO_SAVED",
                    session_id=session_id,
                    audio_size_bytes=len(audio_bytes),
                )

        except Exception as e:
            logger.error(
                "ADD_FULL_AUDIO_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise
