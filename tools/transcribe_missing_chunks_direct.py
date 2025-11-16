#!/usr/bin/env python3
"""Direct Deepgram API call to transcribe missing chunks.

Bypasses service layer to avoid logger compatibility issues.

Created: 2025-11-16
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path

import aiohttp
import h5py

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage import task_repository

CORPUS_PATH = Path(__file__).parent.parent / "storage" / "corpus.h5"


async def transcribe_chunk_direct(audio_bytes: bytes, api_key: str) -> str:
    """Transcribe audio bytes using Deepgram API directly."""
    url = "https://api.deepgram.com/v1/listen"

    params = {
        "model": "nova-2-general",  # nova-2-medical not available for Spanish
        "language": "es",
        "punctuate": "true",
        "diarize": "false",
        "smart_format": "true",
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            params=params,
            headers=headers,
            data=audio_bytes,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            response.raise_for_status()
            result = await response.json()

            # Extract transcript
            transcript = result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
            return transcript


async def transcribe_missing_chunks(session_id: str) -> None:
    """Transcribe chunks with audio but empty transcript."""
    print(f"🔍 Scanning session: {session_id}")

    # Get Deepgram API key from environment
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ ERROR: DEEPGRAM_API_KEY environment variable not set")
        return

    transcribed_count = 0

    with h5py.File(CORPUS_PATH, "r+") as f:
        base_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks"

        if base_path not in f:
            print(f"❌ ERROR: No chunks found at {base_path}")
            return

        chunks_grp = f[base_path]
        chunk_keys = sorted(chunks_grp.keys(), key=lambda x: int(x.split("_")[1]))

        print(f"📊 Found {len(chunk_keys)} chunks total")
        print()

        for chunk_key in chunk_keys:
            chunk_grp = chunks_grp[chunk_key]
            chunk_idx = int(chunk_key.split("_")[1])

            # Check if transcript is empty
            transcript = chunk_grp["transcript"][()].decode() if chunk_grp["transcript"][()] else ""

            if transcript:
                print(f"✅ Chunk {chunk_idx}: OK (has transcript)")
                continue

            # Get audio
            audio_bytes = bytes(chunk_grp["audio.webm"][()])

            if not audio_bytes:
                print(f"⚠️  Chunk {chunk_idx}: No audio data")
                continue

            audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:8]
            print(f"🎙️  Chunk {chunk_idx}: Transcribing... ({len(audio_bytes):,} bytes, hash={audio_hash})")

            try:
                # Call Deepgram API
                transcript_text = await transcribe_chunk_direct(audio_bytes, api_key)

                if not transcript_text:
                    print(f"⚠️  Chunk {chunk_idx}: Empty transcript returned")
                    continue

                # Update HDF5 with transcript
                chunk_grp["transcript"][()] = transcript_text.encode("utf-8")

                preview = transcript_text[:60] if len(transcript_text) > 60 else transcript_text
                print(f"✅ Chunk {chunk_idx}: Transcribed - \"{preview}...\"")

                transcribed_count += 1

            except Exception as e:
                print(f"❌ Chunk {chunk_idx}: Failed - {str(e)}")

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

        print()
        print(f"✅ Metadata updated: processed_chunks = {new_processed}")
    except Exception as e:
        print(f"⚠️  Metadata update failed: {str(e)}")

    print()
    print(f"🎉 Complete! Transcribed {transcribed_count} chunks")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 transcribe_missing_chunks_direct.py <session_id>")
        print("\nExample:")
        print("  python3 tools/transcribe_missing_chunks_direct.py 070fe4b1-f7f4-4477-ab82-f01f1c010474")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(transcribe_missing_chunks(session_id))
