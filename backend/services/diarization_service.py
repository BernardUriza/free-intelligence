from __future__ import annotations

"""
Diarization Service - Whisper ASR + Qwen Speaker Classification
Card: FI-BACKEND-FEAT-004

Pipeline:
1. Chunk audio (10-30s segments with VAD or fixed intervals)
2. ASR each chunk with faster-whisper
3. Classify speaker role (PACIENTE, MEDICO, DESCONOCIDO) using Qwen/Ollama
4. Merge consecutive segments from same speaker
5. Return structured diarization result

File: backend/diarization_service.py
Created: 2025-10-30
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.logger import get_logger
from backend.whisper_service import is_whisper_available, transcribe_audio

logger = get_logger(__name__)

# Configuration
CHUNK_DURATION_SEC = int(
    os.getenv("DIARIZATION_CHUNK_SEC", "60")
)  # 60s chunks (default for speed, was 30s)
MIN_SEGMENT_DURATION = float(os.getenv("MIN_SEGMENT_SEC", "0.5"))  # Filter <0.5s
# Performance tuning (increase chunk size for 25% speedup, reduce for better speaker granularity)
# Options: 20 (granular), 30 (balanced), 60 (fastest), 120 (very fast but coarse)
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv(
    "LLM_MODEL", os.getenv("DIARIZATION_LLM_MODEL", "qwen2.5:7b-instruct-q4_0")
)
LLM_TEMPERATURE = float(os.getenv("DIARIZATION_LLM_TEMP", "0.1"))  # Low temp for determinism
LLM_TIMEOUT_MS = int(os.getenv("LLM_TIMEOUT_MS", "60000"))  # 60s timeout (was 30s)
LLM_TIMEOUT_SEC = LLM_TIMEOUT_MS / 1000.0
# Kill switches
FI_ENRICHMENT = os.getenv("FI_ENRICHMENT", "on").lower() == "on"
ENABLE_LLM_CLASSIFICATION = (
    os.getenv("ENABLE_LLM_CLASSIFICATION", "false").lower() == "true"
)  # OFF by default (3-4x speedup)
WHISPER_MODEL_SIZE = os.getenv(
    "WHISPER_MODEL_SIZE", "base"
)  # Options: tiny, base (default for speed), small, medium, large-v3

# Ollama availability cache (check once at startup)
_ollama_available = None


@dataclass
class DiarizationSegment:
    """Single diarized segment with speaker label."""

    start_time: float  # seconds
    end_time: float  # seconds
    speaker: str  # PACIENTE | MEDICO | DESCONOCIDO
    text: str  # transcribed text
    confidence: Optional[float] = None  # optional confidence score


@dataclass
class DiarizationResult:
    """Complete diarization result with metadata."""

    session_id: str
    audio_file_path: str
    audio_file_hash: str
    duration_sec: float
    language: str
    model_asr: str
    model_llm: str
    segments: list[DiarizationSegment]
    processing_time_sec: float
    created_at: str


def check_ollama_available() -> bool:
    """
    Check if Ollama is available at OLLAMA_BASE_URL.

    Caches result to avoid repeated checks.

    Returns:
        True if Ollama is reachable, False otherwise
    """
    global _ollama_available

    if _ollama_available is not None:
        return _ollama_available

    try:
        import requests

        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        _ollama_available = response.status_code == 200

        if _ollama_available:
            logger.info("OLLAMA_AVAILABLE", url=OLLAMA_BASE_URL, model=OLLAMA_MODEL)
        else:
            logger.warning("OLLAMA_UNREACHABLE", url=OLLAMA_BASE_URL, status=response.status_code)

        return _ollama_available
    except Exception as e:
        logger.warning("OLLAMA_CHECK_FAILED", url=OLLAMA_BASE_URL, error=str(e))
        _ollama_available = False
        return False


def compute_audio_hash(file_path: Path) -> str:
    """Compute SHA256 hash of audio file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def chunk_audio_fixed(
    audio_path: Path, chunk_sec: int = CHUNK_DURATION_SEC
) -> list[tuple[float, float]]:
    """
    Create fixed-duration chunks for audio file.

    Returns list of (start_sec, end_sec) tuples.
    Uses ffprobe to get duration, then creates chunks.
    """
    import subprocess

    # Get audio duration using ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        duration = float(result.stdout.strip())
    except Exception:
        logger.warning("FFPROBE_FAILED")
        duration = 30.0  # fallback

    # Create chunks
    chunks = []
    current = 0.0
    while current < duration:
        end = min(current + chunk_sec, duration)
        chunks.append((current, end))
        current = end

    logger.info(
        "AUDIO_CHUNKED", total_duration=duration, chunk_count=len(chunks), chunk_sec=chunk_sec
    )
    return chunks


def extract_chunk(audio_path: Path, start_sec: float, end_sec: float, output_path: Path) -> bool:
    """
    Extract audio chunk using ffmpeg.

    Args:
        audio_path: source audio file
        start_sec: start time in seconds
        end_sec: end time in seconds
        output_path: destination for chunk

    Returns:
        True if successful, False otherwise
    """
    import subprocess

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
                str(output_path),
                "-loglevel",
                "error",
            ],
            check=True,
            timeout=30,
        )
        return True
    except Exception as e:
        logger.error("CHUNK_EXTRACTION_FAILED", start=start_sec, end=end_sec, error=str(e))
        return False


def classify_speaker_with_llm(text: str, context_before: str = "", context_after: str = "") -> str:
    """
    Classify speaker role using Qwen via Ollama.

    Gracefully degrades to DESCONOCIDO if:
    - LLM classification is disabled (ENABLE_LLM_CLASSIFICATION=false)
    - Ollama is not available
    - Request times out or fails

    Args:
        text: transcribed text for this segment
        context_before: previous segment text (optional)
        context_after: next segment text (optional)

    Returns:
        Speaker label: PACIENTE | MEDICO | DESCONOCIDO
    """
    # Early exit if LLM classification is disabled (kill switches)
    if not FI_ENRICHMENT or not ENABLE_LLM_CLASSIFICATION:
        logger.debug(
            "LLM_CLASSIFICATION_DISABLED",
            fi_enrichment=FI_ENRICHMENT,
            enable_llm=ENABLE_LLM_CLASSIFICATION,
            text_preview=text[:50],
        )
        return "DESCONOCIDO"

    # Early exit if Ollama is not available
    if not check_ollama_available():
        logger.debug("LLM_UNAVAILABLE", text_preview=text[:50])
        return "DESCONOCIDO"

    # Try to use Ollama for classification
    try:
        import requests

        # Build prompt with context
        prompt = f"""Clasifica el hablante del siguiente segmento de consulta médica.

Contexto previo: "{context_before}"
Segmento actual: "{text}"
Contexto siguiente: "{context_after}"

Responde SOLO con una de estas tres palabras:
- PACIENTE (si habla el paciente o acompañante)
- MEDICO (si habla el médico o profesional de salud)
- DESCONOCIDO (si no está claro)

Clasificación:"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "temperature": LLM_TEMPERATURE,
                "stream": False,
                "options": {"num_predict": 20},  # Limit tokens
            },
            timeout=LLM_TIMEOUT_SEC,
        )

        if response.status_code == 200:
            result = response.json()
            classification = result.get("response", "").strip().upper()

            # Extract first valid label
            if "PACIENTE" in classification:
                logger.debug(
                    "LLM_CLASSIFICATION_SUCCESS", speaker="PACIENTE", text_preview=text[:30]
                )
                return "PACIENTE"
            elif "MEDICO" in classification or "MÉDICO" in classification:
                logger.debug("LLM_CLASSIFICATION_SUCCESS", speaker="MEDICO", text_preview=text[:30])
                return "MEDICO"
            else:
                logger.debug("LLM_CLASSIFICATION_AMBIGUOUS", text_preview=text[:30])
                return "DESCONOCIDO"
        else:
            logger.warning(
                "LLM_CLASSIFICATION_FAILED", status=response.status_code, text_preview=text[:30]
            )
            return "DESCONOCIDO"

    except requests.exceptions.Timeout:
        logger.warning("LLM_TIMEOUT", timeout=LLM_TIMEOUT_SEC, text_preview=text[:30])
        return "DESCONOCIDO"
    except Exception:
        logger.error("LLM_REQUEST_ERROR")
        return "DESCONOCIDO"


def merge_consecutive_segments(segments: list[DiarizationSegment]) -> list[DiarizationSegment]:
    """
    Merge consecutive segments from the same speaker.

    Args:
        segments: list of diarized segments

    Returns:
        Merged list with consecutive same-speaker segments combined
    """
    if not segments:
        return []

    merged = [segments[0]]

    for seg in segments[1:]:
        last = merged[-1]

        # Check if same speaker and gap < 1 second
        if last.speaker == seg.speaker and (seg.start_time - last.end_time) < 1.0:
            # Merge: extend time and concatenate text
            merged[-1] = DiarizationSegment(
                start_time=last.start_time,
                end_time=seg.end_time,
                speaker=last.speaker,
                text=f"{last.text} {seg.text}".strip(),
                confidence=None,
            )
        else:
            merged.append(seg)

    logger.info("SEGMENTS_MERGED", original=len(segments))
    return merged


def diarize_audio(
    audio_path: Path,
    session_id: str,
    language: str = "es",
    persist: bool = False,
    progress_callback=None,
) -> DiarizationResult:
    """
    Main diarization pipeline.

    Args:
        audio_path: path to audio file
        session_id: session identifier
        language: language code (default: es)
        persist: if True, save results to disk

    Returns:
        DiarizationResult with segments and metadata
    """
    start_time = time.time()

    # Log configuration and diagnostics
    logger.info(
        "DIARIZATION_START",
        session_id=session_id,
        audio_path=str(audio_path),
        audio_exists=audio_path.exists(),
        whisper_model=WHISPER_MODEL_SIZE,
        llm_enabled=ENABLE_LLM_CLASSIFICATION,
        llm_url=OLLAMA_BASE_URL if ENABLE_LLM_CLASSIFICATION else "N/A",
        llm_model=OLLAMA_MODEL if ENABLE_LLM_CLASSIFICATION else "N/A",
        llm_timeout=LLM_TIMEOUT_SEC if ENABLE_LLM_CLASSIFICATION else "N/A",
        chunk_duration=CHUNK_DURATION_SEC,
    )

    # Check Whisper availability
    if not is_whisper_available():
        raise RuntimeError("Whisper not available - cannot perform diarization")

    # Compute audio hash
    try:
        audio_hash = compute_audio_hash(audio_path)
        logger.info(
            "DIARIZATION_START",
            session_id=session_id,
            audio_path=str(audio_path),
            audio_hash=audio_hash,
        )
    except FileNotFoundError as e:
        logger.error(
            "AUDIO_FILE_NOT_FOUND",
            session_id=session_id,
            audio_path=str(audio_path),
            audio_path_absolute=str(audio_path.absolute()),
            cwd=str(Path.cwd()),
            error=str(e),
        )
        raise

    # Step 1: Create chunks
    chunks = chunk_audio_fixed(audio_path, CHUNK_DURATION_SEC)

    # Step 2: Create temp directory for chunks
    chunk_dir = Path(f"/tmp/diarization_chunks_{session_id}")
    chunk_dir.mkdir(exist_ok=True)

    segments = []

    try:
        total_chunks = len(chunks)

        # Initialize progress callback with total
        if progress_callback:
            progress_callback(10, 0, total_chunks, "CHUNKS_INITIALIZED")

        # Step 3: Process each chunk
        for i, (start_sec, end_sec) in enumerate(chunks):
            chunk_path = chunk_dir / f"chunk_{i:04d}.wav"

            # Extract chunk
            if not extract_chunk(audio_path, start_sec, end_sec, chunk_path):
                logger.warning("CHUNK_SKIP", chunk_index=i, reason="extraction_failed")
                continue

            # Emit event: Whisper transcription start
            if progress_callback:
                progress_callback(
                    10 + int(i / total_chunks * 85), i, total_chunks, "WHISPER_TRANSCRIPTION_START"
                )

            # Transcribe chunk
            transcription = transcribe_audio(chunk_path, language=language, vad_filter=True)

            if not transcription.get("available", False):
                logger.warning("CHUNK_SKIP", chunk_index=i, reason="transcription_unavailable")
                continue

            text = transcription.get("text", "").strip()

            # Skip empty or very short segments
            if not text or len(text) < 3:
                logger.debug("CHUNK_SKIP", chunk_index=i, reason="text_empty")
                continue

            # Emit event: Whisper transcription complete
            if progress_callback:
                progress_callback(
                    10 + int(i / total_chunks * 85),
                    i,
                    total_chunks,
                    "WHISPER_TRANSCRIPTION_COMPLETE",
                )

            # Build context for LLM
            context_before = segments[-1].text if segments else ""
            context_after = ""  # We don't have future context yet

            # Classify speaker
            speaker = classify_speaker_with_llm(text, context_before, context_after)

            # Create segment
            seg = DiarizationSegment(
                start_time=start_sec, end_time=end_sec, speaker=speaker, text=text
            )
            segments.append(seg)

            logger.info("CHUNK_PROCESSED", chunk_index=i, speaker=speaker, text_len=len(text))

            # Emit event: Chunk classified (every 2 chunks or last chunk)
            if progress_callback and (i % 2 == 0 or i == total_chunks - 1):
                progress_pct = 10 + int((i + 1) / total_chunks * 85)
                progress_callback(progress_pct, i + 1, total_chunks, "CHUNK_CLASSIFIED")
                logger.debug(
                    "PROGRESS_UPDATE", chunk=i + 1, total=total_chunks, progress=progress_pct
                )

        # Step 4: Merge consecutive segments
        if progress_callback:
            progress_callback(95, total_chunks, total_chunks, "MERGE_STARTED")

        segments = merge_consecutive_segments(segments)

        if progress_callback:
            progress_callback(98, total_chunks, total_chunks, "MERGE_COMPLETE")

        # Step 5: Get total duration
        duration = chunks[-1][1] if chunks else 0.0

        # Step 6: Create result
        result = DiarizationResult(
            session_id=session_id,
            audio_file_path=str(audio_path),
            audio_file_hash=audio_hash,
            duration_sec=duration,
            language=language,
            model_asr="faster-whisper/large-v3",
            model_llm=OLLAMA_MODEL,
            segments=segments,
            processing_time_sec=time.time() - start_time,
            created_at=datetime.now(UTC).isoformat() + "Z",
        )

        logger.info(
            "DIARIZATION_COMPLETE",
            session_id=session_id,
            segments_count=len(segments),
            processing_time=result.processing_time_sec,
        )

        # Optionally persist
        if persist:
            _persist_result(result)

        return result

    finally:
        # Cleanup temp chunks
        import shutil

        if chunk_dir.exists():
            shutil.rmtree(chunk_dir, ignore_errors=True)
            logger.debug("CHUNKS_CLEANED", chunk_dir=str(chunk_dir))


def _persist_result(result: DiarizationResult) -> Path:
    """
    Persist diarization result to disk with manifest.

    Returns:
        Path to saved result directory
    """
    export_dir = Path("storage/exports/diarization") / result.session_id
    export_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = export_dir / "result.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)

    # Save Markdown
    md_path = export_dir / "result.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Diarización - Sesión {result.session_id}\n\n")
        f.write(f"**Duración:** {result.duration_sec:.1f}s\n")
        f.write(f"**Idioma:** {result.language}\n")
        f.write(f"**Modelo ASR:** {result.model_asr}\n")
        f.write(f"**Modelo LLM:** {result.model_llm}\n")
        f.write(f"**Segmentos:** {len(result.segments)}\n\n")
        f.write("---\n\n")

        for i, seg in enumerate(result.segments, 1):
            f.write(f"## Segmento {i} - {seg.speaker}\n\n")
            f.write(f"**Tiempo:** {seg.start_time:.1f}s - {seg.end_time:.1f}s\n\n")
            f.write(f"{seg.text}\n\n")

    # Create manifest
    manifest = {
        "session_id": result.session_id,
        "audio_file_hash": result.audio_file_hash,
        "result_files": {"json": str(json_path.name), "markdown": str(md_path.name)},
        "created_at": result.created_at,
        "processing_time_sec": result.processing_time_sec,
    }

    manifest_path = export_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "RESULT_PERSISTED",
        export_dir=str(export_dir),
        files=["result.json", "result.md", "manifest.json"],
    )
    return export_dir


def export_diarization(result: DiarizationResult, format: str = "json") -> str:
    """
    Export diarization result to specified format.

    Args:
        result: DiarizationResult object
        format: export format (json | markdown)

    Returns:
        Exported content as string
    """
    if format == "json":
        return json.dumps(asdict(result), indent=2, ensure_ascii=False)

    elif format == "markdown":
        lines = [
            f"# Diarización - Sesión {result.session_id}",
            "",
            f"**Duración:** {result.duration_sec:.1f}s",
            f"**Idioma:** {result.language}",
            f"**Modelo ASR:** {result.model_asr}",
            f"**Modelo LLM:** {result.model_llm}",
            f"**Segmentos:** {len(result.segments)}",
            f"**Hash Audio:** {result.audio_file_hash[:16]}...",
            "",
            "---",
            "",
        ]

        for i, seg in enumerate(result.segments, 1):
            lines.extend(
                [
                    f"## Segmento {i} - {seg.speaker}",
                    "",
                    f"**Tiempo:** {seg.start_time:.1f}s - {seg.end_time:.1f}s",
                    "",
                    seg.text,
                    "",
                ]
            )

        return "\n".join(lines)

    else:
        raise ValueError(f"Unsupported format: {format}")
