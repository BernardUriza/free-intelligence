"""Logic for session checkpoint audio concatenation.

Author: Bernard Uriza Orozco
Created: 2025-12-07
"""

from __future__ import annotations

import h5py
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.logger import get_logger
from backend.storage.task_repository import CORPUS_PATH

logger = get_logger(__name__)


def perform_checkpoint_concatenation(
    session_id: str,
    last_checkpoint_idx: int,
    new_checkpoint_idx: int,
) -> tuple[int, bytes]:
    """Perform audio concatenation for checkpoint.

    Args:
        session_id: Session UUID
        last_checkpoint_idx: Last checkpoint index
        new_checkpoint_idx: New checkpoint index

    Returns:
        Tuple of (chunks_concatenated, full_audio_bytes)

    Raises:
        ValueError: If concatenation fails
    """
    # Safety: limit number of chunks to concatenate in one checkpoint to avoid OOM/abuse
    max_chunks_env = int(os.getenv("MAX_CONCAT_CHUNKS", "500"))

    audio_files = []
    chunks_concatenated = 0

    # Use TemporaryDirectory to ensure cleanup on any failure
    with tempfile.TemporaryDirectory(prefix="checkpoint_") as _tmpdir:
        temp_dir = Path(_tmpdir)

        with h5py.File(CORPUS_PATH, "r") as f:
            # Get all chunk keys from HDF5 (don't assume sequential from 0)
            chunks_group_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks"

            if chunks_group_path not in f:
                logger.warning("NO_CHUNKS_GROUP", session_id=session_id)
                raise ValueError(f"No chunks found for session {session_id}")

            chunks_group = f[chunks_group_path]

            # Extract chunk numbers and sort them
            chunk_numbers = []
            for key in chunks_group:
                if key.startswith("chunk_"):
                    try:
                        chunk_num = int(key.split("_")[1])
                        chunk_numbers.append(chunk_num)
                    except (ValueError, IndexError):
                        logger.warning("INVALID_CHUNK_KEY", key=key)
                        continue

            chunk_numbers.sort()

            logger.info(
                "CHECKPOINT_CHUNK_DISCOVERY",
                session_id=session_id,
                available_chunks=chunk_numbers,
                last_checkpoint=last_checkpoint_idx,
                requested_checkpoint=new_checkpoint_idx,
            )

            # Filter chunks in checkpoint range
            for chunk_idx in chunk_numbers:
                if last_checkpoint_idx < chunk_idx <= new_checkpoint_idx:
                    chunk_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_idx}"
                    if chunk_path not in f:
                        logger.warning("CHUNK_GROUP_MISSING", session_id=session_id, chunk_idx=chunk_idx)
                        continue

                    chunk_group = f[chunk_path]

                    # Check if audio exists and is not empty
                    if "audio.webm" in chunk_group:  # type: ignore[operator]
                        audio_data = chunk_group["audio.webm"][()]

                        # Convert numpy array to bytes properly
                        if hasattr(audio_data, "tobytes"):
                            audio_bytes = audio_data.tobytes()
                        elif isinstance(audio_data, bytes):
                            audio_bytes = audio_data
                        else:
                            audio_bytes = bytes(audio_data)

                        # Skip empty audio files
                        if len(audio_bytes) == 0:
                            logger.warning("CHUNK_AUDIO_EMPTY", session_id=session_id, chunk_idx=chunk_idx)
                            continue

                        # Save to temp file
                        temp_audio = temp_dir / f"chunk_{chunk_idx:03d}.webm"
                        temp_audio.write_bytes(audio_bytes)
                        audio_files.append(temp_audio)
                        chunks_concatenated += 1

                        # Safety guard
                        if chunks_concatenated > max_chunks_env:
                            logger.error(
                                "CHECKPOINT_TOO_MANY_CHUNKS",
                                session_id=session_id,
                                chunks=chunks_concatenated,
                                max_allowed=max_chunks_env,
                            )
                            raise ValueError(
                                f"Too many chunks to concatenate in a single checkpoint ({chunks_concatenated}). "
                                f"Increase MAX_CONCAT_CHUNKS if necessary."
                            )
                    else:
                        logger.warning("CHUNK_NO_AUDIO", session_id=session_id, chunk_idx=chunk_idx)

        if not audio_files:
            logger.warning(
                "NO_NEW_CHUNKS_TO_CONCATENATE",
                session_id=session_id,
                range=f"{last_checkpoint_idx + 1} to {new_checkpoint_idx}",
            )
            return 0, b""

        # Check if full_audio.webm exists (read from HDF5)
        existing_audio_bytes: bytes | None = None
        with h5py.File(CORPUS_PATH, "r") as f:
            full_audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
            if full_audio_path in f:
                existing_audio_data = f[full_audio_path][()]

                # Convert numpy array to bytes properly
                if hasattr(existing_audio_data, "tobytes"):
                    existing_audio_bytes = existing_audio_data.tobytes()
                elif isinstance(existing_audio_data, bytes):
                    existing_audio_bytes = existing_audio_data
                else:
                    existing_audio_bytes = bytes(existing_audio_data)

                if existing_audio_bytes is not None:
                    logger.info("EXISTING_AUDIO_FOUND", session_id=session_id, size_bytes=len(existing_audio_bytes))

        # Concatenate: existing + new chunks
        concat_list_files = []

        if existing_audio_bytes:
            # Save existing audio to temp
            existing_audio_file = temp_dir / "existing_audio.webm"
            existing_audio_file.write_bytes(existing_audio_bytes)
            concat_list_files.append(existing_audio_file)

        concat_list_files.extend(audio_files)

        # Create ffmpeg concat file list
        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for audio_file in concat_list_files:
                f.write(f"file '{audio_file}'\n")

        # Ensure ffmpeg is available
        if shutil.which("ffmpeg") is None:
            logger.error("FFMPEG_NOT_FOUND", session_id=session_id)
            raise RuntimeError("ffmpeg is not installed on the server; cannot concatenate audio.")

        # Concatenate using ffmpeg (re-encode to WebM/Opus for consistency)
        output_file = temp_dir / "full_audio_new.webm"
        ffmpeg_cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:a",
            "libopus",  # Encode to Opus codec (WebM standard)
            "-b:a",
            "128k",  # 128 kbps bitrate
            str(output_file),
            "-loglevel",
            "error",
            "-y",
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True, timeout=120)
        except subprocess.CalledProcessError as cpe:
            logger.error("FFMPEG_CONCAT_FAILED", session_id=session_id, error=str(cpe), exc_info=True)
            raise RuntimeError(f"ffmpeg failed to concatenate audio: {cpe}") from cpe

        # Read concatenated audio
        full_audio_bytes = output_file.read_bytes()

    return chunks_concatenated, full_audio_bytes
