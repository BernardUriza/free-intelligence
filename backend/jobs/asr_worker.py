#!/usr/bin/env python3
"""
Free Intelligence - ASR Worker
Faster-whisper optimized for CPU (DS923+)

Watches IN_DIR for audio files, transcribes them, outputs JSON to OUT_DIR.

Environment Variables:
    IN_DIR: Input directory for audio files
    OUT_DIR: Output directory for JSON results
    LOG_DIR: Log directory
    MODEL: Whisper model size (tiny|base|small|medium|large-v3)
    LANG: Language code (es, en, etc.)
    COMPUTE: Compute type (int8|float16|float32)
    VAD: Enable VAD (true|false)
    BEAM: Beam size (1-5)
    VAD_MIN_SILENCE_MS: Min silence duration for split (ms)
    POLL_INTERVAL: Seconds between directory scans
    MAX_WORKERS: Max parallel transcriptions
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from faster_whisper import WhisperModel

# Configuration from environment
MODEL_SIZE = os.getenv("MODEL", "small")
COMPUTE_TYPE = os.getenv("COMPUTE", "int8")
LANGUAGE = os.getenv("LANG", "es")
VAD_ENABLED = os.getenv("VAD", "true").lower() == "true"
BEAM_SIZE = int(os.getenv("BEAM", "1"))
VAD_MIN_SILENCE = int(os.getenv("VAD_MIN_SILENCE_MS", "300"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))

IN_DIR = Path(os.getenv("IN_DIR", "/data/ready"))
OUT_DIR = Path(os.getenv("OUT_DIR", "/data/asr/json"))
LOG_DIR = Path(os.getenv("LOG_DIR", "/data/asr/logs"))

# Setup logging - use fallback path if /data is read-only
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError):
    # Fallback to local storage
    LOG_DIR = Path("./storage/logs/asr")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "worker.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Create PID file for healthcheck
with open("/tmp/worker.pid", "w") as f:
    f.write(str(os.getpid()))

logger.info("ASR Worker starting...")
logger.info(f"  Model: {MODEL_SIZE} ({COMPUTE_TYPE})")
logger.info(f"  Language: {LANGUAGE}")
logger.info(f"  VAD: {VAD_ENABLED} (min_silence={VAD_MIN_SILENCE}ms)")
logger.info(f"  Beam size: {BEAM_SIZE}")
logger.info(f"  Input: {IN_DIR}")
logger.info(f"  Output: {OUT_DIR}")
logger.info(f"  Max workers: {MAX_WORKERS}")

# Initialize Whisper model
logger.info("Loading Whisper model...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE, num_workers=MAX_WORKERS)
logger.info("Model loaded successfully")

# Create output directory - use fallback if /data is read-only
try:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError):
    # Fallback to local storage
    OUT_DIR = Path("./storage/asr/json")
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def transcribe_file(audio_path: Path) -> dict:
    """
    Transcribe a single audio file.

    Returns:
        Dict with transcription results
    """
    start_time = time.time()
    output_path = OUT_DIR / f"{audio_path.name}.json"

    # Skip if already processed
    if output_path.exists():
        logger.debug(f"SKIP (already processed): {audio_path.name}")
        return {"status": "skipped", "file": audio_path.name}

    try:
        logger.info(f"TRANSCRIBE START: {audio_path.name}")

        # Transcribe with VAD if enabled
        vad_params = (
            {"min_silence_duration_ms": VAD_MIN_SILENCE, "speech_pad_ms": 400}
            if VAD_ENABLED
            else None
        )

        segments, info = model.transcribe(
            str(audio_path),
            language=LANGUAGE,
            vad_filter=VAD_ENABLED,
            vad_parameters=vad_params,
            beam_size=BEAM_SIZE,
            best_of=BEAM_SIZE,
        )

        # Convert generator to list and format
        segments_list = []
        for seg in segments:
            segments_list.append(
                {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
            )

        # Build result
        result = {
            "file": audio_path.name,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_sec": round(info.duration, 2),
            "segments": segments_list,
            "segment_count": len(segments_list),
            "model": MODEL_SIZE,
            "compute_type": COMPUTE_TYPE,
            "vad_enabled": VAD_ENABLED,
            "processing_time_sec": round(time.time() - start_time, 2),
        }

        # Write JSON output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(
            f"TRANSCRIBE COMPLETE: {audio_path.name} "
            f"({len(segments_list)} segments, {result['processing_time_sec']}s)"
        )

        return {"status": "success", "file": audio_path.name, "segments": len(segments_list)}

    except Exception as e:
        logger.error(f"TRANSCRIBE ERROR: {audio_path.name} - {e}")
        return {"status": "error", "file": audio_path.name, "error": str(e)}


def scan_and_process():
    """
    Scan input directory and process new audio files.
    """
    # Supported formats
    patterns = ["*.wav", "*.mp3", "*.m4a", "*.mp4", "*.flac", "*.ogg", "*.webm"]
    audio_files = []

    for pattern in patterns:
        audio_files.extend(IN_DIR.glob(pattern))

    if not audio_files:
        return

    logger.info(f"Found {len(audio_files)} audio files")

    # Process files in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(transcribe_file, f): f for f in audio_files}

        for future in as_completed(futures):
            result = future.result()
            if result["status"] == "success":
                logger.info(f"✓ {result['file']} → {result['segments']} segments")
            elif result["status"] == "error":
                logger.error(f"✗ {result['file']} → {result['error']}")


def main():
    """
    Main worker loop.
    """
    logger.info("Worker ready - monitoring directory...")

    iteration = 0
    while True:
        try:
            scan_and_process()
            iteration += 1

            if iteration % 30 == 0:  # Log heartbeat every ~60s
                logger.info(f"Worker alive (iteration {iteration})")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(POLL_INTERVAL * 2)  # Backoff on error


if __name__ == "__main__":
    main()
