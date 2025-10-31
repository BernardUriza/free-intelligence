"""
Whisper Transcription Service
Card: FI-BACKEND-FEAT-003

Provides audio transcription using faster-whisper with:
- Singleton WhisperModel (cached instance)
- CPU-optimized int8_float16 quantization
- VAD filtering for noise reduction
- Spanish language forcing
- Graceful degradation if dependencies missing

File: backend/whisper_service.py
Created: 2025-10-30
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.logger import get_logger

logger = get_logger(__name__)

# Whisper configuration
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")  # small (default for CPU), tiny, base, medium, large-v3
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8 fastest on CPU (50-70% faster than float16)
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu or cuda
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")  # Force Spanish
# CPU optimization (DS923+: Ryzen R1600, 4 threads → use 3, leave 1 free)
CPU_THREADS = int(os.getenv("ASR_CPU_THREADS", "3"))
NUM_WORKERS = int(os.getenv("ASR_NUM_WORKERS", "1"))

# Global singleton instance
_whisper_model_instance: Optional[Any] = None
_whisper_available: bool = False

# Check if faster-whisper is available
try:
    from faster_whisper import WhisperModel

    _whisper_available = True
    logger.info("WHISPER_AVAILABLE", model_size=WHISPER_MODEL_SIZE, compute_type=WHISPER_COMPUTE_TYPE)
except ImportError:
    logger.warning(
        "WHISPER_NOT_AVAILABLE",
        reason="faster-whisper not installed",
        install_cmd="pip install faster-whisper",
    )
    WhisperModel = None  # type: ignore


def is_whisper_available() -> bool:
    """
    Check if Whisper transcription is available.

    Returns:
        True if faster-whisper is installed and model loaded
    """
    return _whisper_available


def get_whisper_model() -> Optional[Any]:
    """
    Get singleton WhisperModel instance (lazy loading).

    Returns:
        WhisperModel instance or None if not available

    Notes:
        - First call will download model (~3GB for large-v3)
        - Subsequent calls return cached instance
        - Returns None if faster-whisper not installed
    """
    global _whisper_model_instance

    if not _whisper_available:
        return None

    if _whisper_model_instance is None:
        try:
            # Log cold start (FI-UI-FEAT-206)
            logger.warning(
                "WHISPER_MODEL_COLD_START",
                model_size=WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                message="First transcription will be slow (~10-30s for model load)"
            )

            _whisper_model_instance = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                cpu_threads=CPU_THREADS,
                num_workers=NUM_WORKERS,
                download_root=os.getenv("WHISPER_CACHE_DIR", None),
            )

            logger.info(
                "WHISPER_MODEL_LOADED",
                model_size=WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                message="Model ready for transcription"
            )
        except Exception as e:
            logger.error(
                "WHISPER_MODEL_LOAD_FAILED",
                error=str(e),
                model_size=WHISPER_MODEL_SIZE,
            )
            return None

    return _whisper_model_instance


def transcribe_audio(
    audio_path: Path,
    language: Optional[str] = None,
    vad_filter: bool = True,
) -> Dict[str, Any]:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file (WAV, MP3, M4A, WEBM supported)
        language: Language code (default: "es" for Spanish)
        vad_filter: Enable Voice Activity Detection filtering

    Returns:
        Dict with:
            - text: str (full transcription, joined segments)
            - segments: List[Dict] (individual segments with timestamps)
            - language: str (detected or forced language)
            - duration: float (audio duration in seconds)
            - available: bool (whether transcription succeeded)

    Notes:
        - If faster-whisper not available, returns mock data
        - Synchronous transcription (no streaming)
        - Uses VAD filter to reduce noise
    """
    if language is None:
        language = WHISPER_LANGUAGE

    # Check if Whisper is available
    if not is_whisper_available():
        logger.warning(
            "WHISPER_TRANSCRIPTION_SKIPPED",
            reason="faster-whisper not available",
            audio_path=str(audio_path),
        )
        return {
            "text": "[Transcription not available - faster-whisper not installed]",
            "segments": [],
            "language": language,
            "duration": 0.0,
            "available": False,
        }

    # Get model
    model = get_whisper_model()
    if model is None:
        logger.error(
            "WHISPER_MODEL_NOT_LOADED",
            audio_path=str(audio_path),
        )
        return {
            "text": "[Transcription failed - model not loaded]",
            "segments": [],
            "language": language,
            "duration": 0.0,
            "available": False,
        }

    try:
        logger.info(
            "WHISPER_TRANSCRIPTION_START",
            audio_path=str(audio_path),
            language=language,
            vad_filter=vad_filter,
        )

        # Transcribe
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=vad_filter,
            beam_size=5,  # Balance between speed and accuracy
        )

        # Collect segments
        segments_list = []
        full_text_parts = []

        for segment in segments_iter:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            segments_list.append(segment_dict)
            full_text_parts.append(segment.text.strip())

        # Join all segments
        full_text = " ".join(full_text_parts)

        logger.info(
            "WHISPER_TRANSCRIPTION_COMPLETE",
            audio_path=str(audio_path),
            language=info.language,
            duration=info.duration,
            segments_count=len(segments_list),
            text_length=len(full_text),
        )

        return {
            "text": full_text,
            "segments": segments_list,
            "language": info.language,
            "duration": info.duration,
            "available": True,
        }

    except Exception as e:
        logger.error(
            "WHISPER_TRANSCRIPTION_FAILED",
            audio_path=str(audio_path),
            error=str(e),
        )
        return {
            "text": f"[Transcription failed: {str(e)}]",
            "segments": [],
            "language": language,
            "duration": 0.0,
            "available": False,
        }


def convert_audio_to_wav(input_path: Path, output_path: Path) -> bool:
    """
    Convert audio file to WAV format using ffmpeg.

    Args:
        input_path: Input audio file
        output_path: Output WAV file path

    Returns:
        True if conversion succeeded, False otherwise

    Notes:
        - Requires ffmpeg binary installed on system
        - Requires ffmpeg-python package
        - If not available, returns False
    """
    try:
        import ffmpeg

        logger.info(
            "AUDIO_CONVERSION_START",
            input_path=str(input_path),
            output_path=str(output_path),
        )

        # Convert to WAV (16kHz mono for Whisper optimization)
        stream = ffmpeg.input(str(input_path))
        stream = ffmpeg.output(stream, str(output_path), ar=16000, ac=1)
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        logger.info(
            "AUDIO_CONVERSION_COMPLETE",
            input_path=str(input_path),
            output_path=str(output_path),
        )
        return True

    except ImportError:
        logger.warning(
            "AUDIO_CONVERSION_SKIPPED",
            reason="ffmpeg-python not installed",
            install_cmd="pip install ffmpeg-python && brew install ffmpeg",
        )
        return False
    except Exception as e:
        logger.error(
            "AUDIO_CONVERSION_FAILED",
            input_path=str(input_path),
            output_path=str(output_path),
            error=str(e),
        )
        return False
