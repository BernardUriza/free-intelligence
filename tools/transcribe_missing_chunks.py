#!/usr/bin/env python3
"""Transcribe chunks that have audio but empty transcript.

Reads directly from HDF5 and calls STT service.

Created: 2025-11-16
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import h5py

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.logger import get_logger
from backend.services.deepgram_service import DeepgramService
from backend.storage import task_repository

logger = get_logger(__name__)

CORPUS_PATH = Path(__file__).parent.parent / "storage" / "corpus.h5"


async def transcribe_missing_chunks(session_id: str) -> None:
    """Transcribe chunks with audio but empty transcript."""
    logger.info("TRANSCRIBE_MISSING_START", session_id=session_id)

    # Get Deepgram API key from environment
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    if not deepgram_api_key:
        logger.error("NO_API_KEY", error="DEEPGRAM_API_KEY not set")
        print("ERROR: DEEPGRAM_API_KEY environment variable not set")
        return

    deepgram = DeepgramService(api_key=deepgram_api_key)
    transcribed_count = 0

    with h5py.File(CORPUS_PATH, "r+") as f:
        base_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks"

        if base_path not in f:
            logger.error("NO_CHUNKS_PATH", session_id=session_id, path=base_path)
            return

        chunks_grp = f[base_path]
        chunk_keys = sorted(chunks_grp.keys(), key=lambda x: int(x.split("_")[1]))

        for chunk_key in chunk_keys:
            chunk_grp = chunks_grp[chunk_key]
            chunk_idx = int(chunk_key.split("_")[1])

            # Check if transcript is empty
            transcript = chunk_grp["transcript"][()].decode() if chunk_grp["transcript"][()] else ""

            if transcript:
                logger.info("CHUNK_OK", session_id=session_id, chunk_idx=chunk_idx)
                continue

            # Get audio
            audio_bytes = bytes(chunk_grp["audio.webm"][()])

            if not audio_bytes:
                logger.warning("NO_AUDIO", session_id=session_id, chunk_idx=chunk_idx)
                continue

            logger.info(
                "TRANSCRIBING_CHUNK",
                session_id=session_id,
                chunk_idx=chunk_idx,
                audio_size=len(audio_bytes),
            )

            try:
                # Call Deepgram STT (async)
                result = await deepgram.transcribe(audio_bytes)
                # TranscriptionResult is a dataclass, not a dict
                transcript_text = result.transcript

                # If empty, try Azure Whisper as fallback
                if not transcript_text or len(transcript_text.strip()) == 0:
                    logger.warning(
                        "EMPTY_TRANSCRIPT_TRYING_AZURE",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                        message="Deepgram returned empty - trying Azure Whisper fallback",
                    )

                    try:
                        # Try Azure Whisper
                        import tempfile

                        from backend.providers.stt import get_stt_provider

                        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                            tmp.write(audio_bytes)
                            tmp_path = tmp.name

                        try:
                            azure = get_stt_provider("azure_whisper")
                            azure_result = azure.transcribe(tmp_path, language="es")

                            if azure_result.text and len(azure_result.text.strip()) > 0:
                                logger.info(
                                    "AZURE_FALLBACK_SUCCESS",
                                    session_id=session_id,
                                    chunk_idx=chunk_idx,
                                    transcript_length=len(azure_result.text),
                                    message="Azure detected speech where Deepgram failed",
                                )
                                transcript_text = azure_result.text
                            else:
                                logger.info(
                                    "CONFIRMED_SILENCE",
                                    session_id=session_id,
                                    chunk_idx=chunk_idx,
                                    message="Both Deepgram and Azure confirmed: no speech detected",
                                )
                                transcript_text = ""
                        finally:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)

                    except Exception as azure_error:
                        logger.error(
                            "AZURE_FALLBACK_FAILED",
                            session_id=session_id,
                            chunk_idx=chunk_idx,
                            error=str(azure_error),
                        )
                        transcript_text = ""  # Use empty if Azure fails

                # Update HDF5 with transcript (even if empty)
                chunk_grp["transcript"][()] = transcript_text.encode("utf-8")

                logger.info(
                    "CHUNK_TRANSCRIBED",
                    session_id=session_id,
                    chunk_idx=chunk_idx,
                    transcript=transcript_text[:50],
                )

                transcribed_count += 1

            except Exception as e:
                logger.error(
                    "TRANSCRIBE_FAILED",
                    session_id=session_id,
                    chunk_idx=chunk_idx,
                    error=str(e),
                    exc_info=True,
                )

    # Update session metadata
    try:
        metadata = task_repository.get_task_metadata(session_id, "TRANSCRIPTION")
        processed_chunks = metadata.get("processed_chunks", 0)
        new_processed = processed_chunks + transcribed_count

        task_repository.update_task_metadata(
            session_id,
            "TRANSCRIPTION",
            {"processed_chunks": new_processed},
        )

        logger.info(
            "METADATA_UPDATED",
            session_id=session_id,
            transcribed=transcribed_count,
            total_processed=new_processed,
        )
    except Exception as e:
        logger.error("METADATA_UPDATE_FAILED", error=str(e))

    logger.info(
        "TRANSCRIBE_COMPLETE",
        session_id=session_id,
        transcribed_count=transcribed_count,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 transcribe_missing_chunks.py <session_id>")
        print("\nExample:")
        print("  python3 tools/transcribe_missing_chunks.py 070fe4b1-f7f4-4477-ab82-f01f1c010474")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(transcribe_missing_chunks(session_id))
