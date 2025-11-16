#!/usr/bin/env python3
"""Reprocess pending chunks that have audio but no transcript.

Created: 2025-11-16
Purpose: Fix chunks that were uploaded but never transcribed due to backend crashes
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.logger import get_logger
from backend.services.transcription_service import TranscriptionService
from backend.storage import task_repository

logger = get_logger(__name__)


async def reprocess_session_chunks(session_id: str) -> None:
    """Reprocess all chunks with audio but no transcript."""
    logger.info("REPROCESS_START", session_id=session_id)

    # Get all chunks
    chunks = task_repository.get_task_chunks(session_id, "TRANSCRIPTION")
    logger.info("CHUNKS_FOUND", session_id=session_id, total=len(chunks))

    service = TranscriptionService()
    pending_chunks = []

    for idx, chunk in enumerate(chunks):
        transcript = chunk.get("transcript", "")
        has_audio = chunk.get("audio_data") is not None

        if has_audio and not transcript:
            pending_chunks.append(idx)
            logger.info(
                "PENDING_CHUNK",
                session_id=session_id,
                chunk_idx=idx,
                audio_size=len(chunk.get("audio_data", b"")),
            )

    if not pending_chunks:
        logger.info("NO_PENDING_CHUNKS", session_id=session_id)
        return

    logger.info("REPROCESSING", session_id=session_id, chunks=pending_chunks)

    # Reprocess each pending chunk
    for idx in pending_chunks:
        chunk = chunks[idx]
        audio_bytes = chunk.get("audio_data", b"")

        if not audio_bytes:
            logger.warning("NO_AUDIO_DATA", session_id=session_id, chunk_idx=idx)
            continue

        try:
            logger.info("REPROCESSING_CHUNK", session_id=session_id, chunk_idx=idx)

            # Use the service to process the chunk
            result = await service.process_chunk(
                session_id=session_id,
                chunk_number=idx,
                audio_bytes=audio_bytes,
                timestamp_start=chunk.get("timestamp_start"),
                timestamp_end=chunk.get("timestamp_end"),
            )

            logger.info(
                "CHUNK_REPROCESSED",
                session_id=session_id,
                chunk_idx=idx,
                status=result.status,
            )

        except Exception as e:
            logger.error(
                "REPROCESS_FAILED",
                session_id=session_id,
                chunk_idx=idx,
                error=str(e),
                exc_info=True,
            )

    logger.info("REPROCESS_COMPLETE", session_id=session_id)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 reprocess_pending_chunks.py <session_id>")
        print("\nExample:")
        print("  python3 tools/reprocess_pending_chunks.py 070fe4b1-f7f4-4477-ab82-f01f1c010474")
        sys.exit(1)

    session_id = sys.argv[1]
    await reprocess_session_chunks(session_id)


if __name__ == "__main__":
    asyncio.run(main())
