#!/usr/bin/env python3
"""
FI DATA CURATION: Recover missing chunks 24-27 from corrupted diarization job
Philosophy: Don't reprocess everything, recover data from existing sources

Job: f2667c96-105b-42c7-b385-2e20417a7fff
Missing: chunks 24-27 (1440s-1680s audio window = 4 minutes)
Strategy: Extract ONLY the 4-minute segment, transcribe it, merge with existing 24 chunks
"""

import sys
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, "/Users/bernardurizaorozco/Documents/free-intelligence")

from backend.logger import get_logger

logger = get_logger(__name__)

# Constants
JOB_ID = "f2667c96-105b-42c7-b385-2e20417a7fff"
AUDIO_PATH = Path(
    "/Users/bernardurizaorozco/Documents/free-intelligence/storage/audio/59c01f36-988c-4770-9815-9ba38842aac7/1762310462413.mp3"
)
HDF5_PATH = "/Users/bernardurizaorozco/Documents/free-intelligence/storage/diarization.h5"
MISSING_CHUNKS = [24, 25, 26, 27]
CHUNK_SIZE_SEC = 60
SEGMENT_START_SEC_CONST = 24 * 60  # 1440 seconds
SEGMENT_END_SEC_CONST = 28 * 60  # 1680 seconds


def extract_audio_segment():
    """Extract audio segment 1440s-1680s (4 minutes) to temp file."""
    try:
        import subprocess

        segment_path = Path("/tmp/missing_segment.mp3")
        print(f"📦 Extracting audio segment {SEGMENT_START_SEC_CONST}s-{SEGMENT_END_SEC_CONST}s...")

        # Use ffmpeg to extract exact time window (macOS-compatible)
        cmd = [
            "ffmpeg",
            "-i",
            str(AUDIO_PATH),
            "-ss",
            str(SEGMENT_START_SEC_CONST),
            "-t",
            "240",  # Duration 240 seconds (4 minutes)
            "-acodec",
            "libmp3lame",
            "-q:a",
            "5",
            "-loglevel",
            "error",
            "-y",
            str(segment_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)

        if result.returncode == 0 and segment_path.exists() and segment_path.stat().st_size > 1000:
            size_mb = segment_path.stat().st_size / (1024 * 1024)
            print(f"   ✓ Extracted {size_mb:.2f} MB")
            return segment_path
        else:
            print("   ⚠️  ffmpeg failed or file too small, will transcribe full audio")
            return None

    except FileNotFoundError:
        print("   ⚠️  ffmpeg not found, will transcribe full audio")
        return None
    except Exception as e:
        print(f"   ⚠️  ffmpeg error: {e}")
        return None


def transcribe_segment(segment_path: Path) -> dict:
    """Transcribe extracted audio segment."""
    try:
        from backend.whisper_service import transcribe_audio

        print("🎤 Transcribing segment...")
        result = transcribe_audio(segment_path, language="es", vad_filter=True)

        if result.get("available"):
            segments = result.get("segments", [])
            print(f"   ✓ Got {len(segments)} segments")
            return result
        else:
            print("   ❌ Transcription failed")
            return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def curate_missing_chunks():
    """Curate missing chunks 24-27 from audio segment."""

    print("🗂️  FI Data Curation - Smart Recovery")
    print(f"   Job ID: {JOB_ID}")
    print(
        f"   Missing chunks: {MISSING_CHUNKS} ({SEGMENT_START_SEC_CONST}s-{SEGMENT_END_SEC_CONST}s)"
    )
    print()

    logger.info(
        "Starting smart data curation",
        extra={
            "job_id": JOB_ID,
            "missing_chunks": MISSING_CHUNKS,
            "segment_window": f"{SEGMENT_START_SEC_CONST}s-{SEGMENT_END_SEC_CONST}s",
            "action": "curate_corrupted_data",
        },
    )

    # 1. Validate audio file
    if not AUDIO_PATH.exists():
        logger.error("Audio file not found", extra={"path": str(AUDIO_PATH)})
        print(f"❌ Audio file not found: {AUDIO_PATH}")
        return False

    audio_size = AUDIO_PATH.stat().st_size / (1024 * 1024)
    print(f"✓ Audio located: {audio_size:.2f} MB")

    # 2. Extract segment (try ffmpeg first for speed)
    segment_path = extract_audio_segment()
    segment_start_sec = SEGMENT_START_SEC_CONST
    segment_end_sec = SEGMENT_END_SEC_CONST

    if segment_path is None:
        print("⚠️  Segment extraction failed, will transcribe full audio (slow)")
        segment_path = AUDIO_PATH
        segment_start_sec = 0
        segment_end_sec = 9999

    # 3. Transcribe segment
    result = transcribe_segment(segment_path)

    if not result:
        print("❌ Transcription failed")
        return False

    segments = result.get("segments", [])

    # 4. Read existing HDF5 data
    try:
        with h5py.File(HDF5_PATH, "r+") as f:
            job_group = f["diarization"][JOB_ID]
            existing_chunks = job_group["chunks"][()]

            print(f"✓ Loaded {len(existing_chunks)} existing chunks from HDF5")

            # 5. Extract text for missing chunks from segments
            new_chunks = []

            for chunk_idx in MISSING_CHUNKS:
                chunk_start_sec = chunk_idx * CHUNK_SIZE_SEC
                chunk_end_sec = (chunk_idx + 1) * CHUNK_SIZE_SEC

                print(f"📝 Chunk {chunk_idx} ({chunk_start_sec}s-{chunk_end_sec}s)...", end=" ")

                # Extract text from segments that overlap this chunk
                chunk_text = ""
                for seg in segments:
                    seg_start = seg.get("start", 0) + segment_start_sec  # Adjust for segment offset
                    seg_end = seg.get("end", 0) + segment_start_sec

                    # Check overlap
                    if seg_start < chunk_end_sec and seg_end > chunk_start_sec:
                        chunk_text += " " + seg.get("text", "")

                chunk_text = chunk_text.strip()

                # Create chunk record
                chunk_record = np.array(
                    [
                        (
                            chunk_idx,
                            float(chunk_start_sec),
                            float(chunk_end_sec),
                            chunk_text,
                            b"DESCONOCIDO",
                            0.0,
                            0.0,
                            datetime.now(UTC).isoformat(),
                        )
                    ],
                    dtype=existing_chunks.dtype,
                )

                new_chunks.append(chunk_record[0])
                print(f"✓ ({len(chunk_text)} chars)")

            # 6. Merge and update HDF5
            if new_chunks:
                merged_chunks = np.concatenate([existing_chunks, np.array(new_chunks)])

                del job_group["chunks"]
                job_group.create_dataset("chunks", data=merged_chunks)

                job_group.attrs["processed_chunks"] = len(merged_chunks)
                job_group.attrs["updated_at"] = datetime.now(UTC).isoformat()
                job_group.attrs["curation_status"] = "recovered"

                print(
                    f"\n✅ Curation complete! {len(existing_chunks)} → {len(merged_chunks)} chunks"
                )

                logger.info(
                    "Data curation complete",
                    extra={
                        "total_chunks": len(merged_chunks),
                        "recovered_chunks": len(new_chunks),
                        "status": "success",
                    },
                )

                return True

    except Exception as e:
        print(f"❌ HDF5 error: {e}")
        logger.error("HDF5 operation failed", extra={"error": str(e)})
        return False

    return False


if __name__ == "__main__":
    success = curate_missing_chunks()
    sys.exit(0 if success else 1)
