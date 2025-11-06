#!/usr/bin/env python3
"""
Process missing chunks 24-27 using the worker's extraction + Whisper transcription.
Uses worker's _extract_chunk to get proper audio segments, then transcribes each.
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, "/Users/bernardurizaorozco/Documents/free-intelligence")

from backend.logger import get_logger
from backend.whisper_service import get_whisper_model, is_whisper_available

logger = get_logger(__name__)

# Constants (match worker)
JOB_ID = "f2667c96-105b-42c7-b385-2e20417a7fff"
AUDIO_PATH = Path(
    "/Users/bernardurizaorozco/Documents/free-intelligence/storage/audio/59c01f36-988c-4770-9815-9ba38842aac7/1762310462413.mp3"
)
HDF5_PATH = Path("/Users/bernardurizaorozco/Documents/free-intelligence/storage/diarization.h5")
CHUNK_SIZE_SEC = 30
CHUNK_OVERLAP_SEC = 0.8


def extract_chunk(audio_path: Path, start_sec: float, end_sec: float, idx: int) -> Path:
    """Extract audio chunk using ffmpeg (worker method)."""
    chunk_path = Path(f"/tmp/diarization_chunk_{idx:04d}.wav")
    duration = end_sec - start_sec

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-ss",
                str(start_sec),
                "-t",
                str(duration),
                "-y",
                str(chunk_path),
                "-loglevel",
                "error",
            ],
            check=True,
            timeout=30,
        )
        return chunk_path if chunk_path.exists() else None
    except Exception as e:
        logger.error("Chunk extraction failed", extra={"idx": idx, "error": str(e)})
        return None


def process_missing_chunks():
    """Process missing chunks 24-27 using worker method."""

    print("🗂️  Processing missing chunks with worker extraction")
    print(f"   Job ID: {JOB_ID}")
    print("   Chunks: 24-27")
    print()

    # Check Whisper
    if not is_whisper_available():
        print("❌ Whisper not available")
        return False

    model = get_whisper_model()
    if model is None:
        print("❌ Whisper model not loaded")
        return False

    # Load HDF5
    try:
        with h5py.File(HDF5_PATH, "r+") as f:
            job_group = f["diarization"][JOB_ID]
            existing_chunks = list(job_group["chunks"][()])

            print(f"✓ Loaded {len(existing_chunks)} existing chunks")
            print()

            new_chunks = []

            # Process chunks 24-27 (chunks need to match existing pattern)
            # Chunk 24: 24*30 = 720s, Chunk 27: 27*30 = 810s + overlap
            for chunk_idx in range(24, 28):
                start_time = chunk_idx * CHUNK_SIZE_SEC
                end_time = start_time + CHUNK_SIZE_SEC + CHUNK_OVERLAP_SEC

                print(
                    f"🎬 Extracting chunk {chunk_idx} ({start_time:.0f}s-{end_time:.0f}s)...",
                    end=" ",
                    flush=True,
                )

                # Extract audio
                chunk_path = extract_chunk(AUDIO_PATH, start_time, end_time, chunk_idx)
                if not chunk_path:
                    print("❌ Extraction failed")
                    return False

                print(f"✓ Extracted {chunk_path.stat().st_size / 1024:.1f}KB", flush=True)

                # Transcribe
                print("🎤 Transcribing...", end=" ", flush=True)
                try:
                    segments_iter, info = model.transcribe(
                        str(chunk_path),
                        language=None,  # Auto-detect
                        vad_filter=True,
                        beam_size=5,
                    )

                    segments = list(segments_iter)
                    text_parts = [seg.text.strip() for seg in segments]
                    full_text = " ".join(text_parts)

                    # Temperature (avg from segments)
                    temps = [seg.avg_logprob for seg in segments if hasattr(seg, "avg_logprob")]
                    temperature = float(np.mean(temps)) if temps else -0.3

                    rtf = 0.2  # Approximate

                    # Create chunk record
                    chunk_record = np.array(
                        [
                            (
                                chunk_idx,
                                float(start_time),
                                float(end_time),
                                full_text,
                                "DESCONOCIDO",
                                temperature,
                                rtf,
                                datetime.now(timezone.utc).isoformat(),
                            )
                        ],
                        dtype=existing_chunks[0].dtype if existing_chunks else None,
                    )

                    new_chunks.append(chunk_record[0])
                    print(f"✓ {len(full_text)} chars")

                    # Cleanup
                    chunk_path.unlink(missing_ok=True)

                except Exception as e:
                    print(f"❌ {e}")
                    chunk_path.unlink(missing_ok=True)
                    return False

            # Merge and save
            if new_chunks:
                print()
                print(f"💾 Merging {len(new_chunks)} new chunks...")

                if existing_chunks:
                    all_chunks = np.concatenate([np.array(existing_chunks), np.array(new_chunks)])
                else:
                    all_chunks = np.array(new_chunks)

                del job_group["chunks"]
                job_group.create_dataset("chunks", data=all_chunks)

                job_group.attrs["processed_chunks"] = len(all_chunks)
                job_group.attrs["total_chunks"] = 28
                job_group.attrs["status"] = "completed"
                job_group.attrs["updated_at"] = datetime.now(timezone.utc).isoformat()

                print(f"\n✅ Complete! {len(existing_chunks)} → {len(all_chunks)} chunks")
                logger.info(
                    "Missing chunks processed",
                    extra={
                        "job_id": JOB_ID,
                        "total_chunks": len(all_chunks),
                    },
                )

                return True

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error("Failed", extra={"error": str(e)})
        import traceback

        traceback.print_exc()
        return False

    return False


if __name__ == "__main__":
    success = process_missing_chunks()
    sys.exit(0 if success else 1)
