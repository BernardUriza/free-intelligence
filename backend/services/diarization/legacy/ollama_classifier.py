"""Ollama integration for speaker classification and text improvement.

Functions:
  - is_ollama_available(): Check if Ollama is reachable
  - classify_speaker(): Classify speaker role (PACIENTE, MEDICO, DESCONOCIDO)
  - improve_text(): Apply ortografía and gramática improvements
"""

from __future__ import annotations

import os
from typing import Optional

import requests

from backend.logger import get_logger

logger = get_logger(__name__)

# Configuration from environment
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv(
    "LLM_MODEL", os.getenv("DIARIZATION_LLM_MODEL", "qwen2.5:7b-instruct-q4_0")
)
LLM_TEMPERATURE = float(os.getenv("DIARIZATION_LLM_TEMP", "0.1"))  # Low temp for determinism
LLM_TIMEOUT_MS = int(os.getenv("LLM_TIMEOUT_MS", "60000"))  # 60s timeout
LLM_TIMEOUT_SEC = LLM_TIMEOUT_MS / 1000.0

# Kill switches
FI_ENRICHMENT = os.getenv("FI_ENRICHMENT", "on").lower() == "on"
ENABLE_LLM_CLASSIFICATION = os.getenv("ENABLE_LLM_CLASSIFICATION", "false").lower() == "true"

# Ollama availability cache (check once at startup)
_ollama_available: Optional[bool] = None


def is_ollama_available() -> bool:
    """Check if Ollama is available at OLLAMA_BASE_URL.

    Caches result to avoid repeated checks.

    Returns:
        True if Ollama is reachable, False otherwise
    """
    global _ollama_available

    if _ollama_available is not None:
        return _ollama_available

    try:
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


def classify_speaker(
    text: str,
    context_before: str = "",
    context_after: str = "",
) -> str:
    """Classify speaker role using Ollama.

    Gracefully degrades to DESCONOCIDO if:
    - LLM classification is disabled (ENABLE_LLM_CLASSIFICATION=false)
    - Ollama is not available
    - Request times out or fails

    Args:
        text: Transcribed text for this segment
        context_before: Previous segment text (optional context for classification)
        context_after: Next segment text (optional context for classification)

    Returns:
        Speaker label: Union[PACIENTE, MEDICO, DESCONOCIDO]
    """
    # Early exit if LLM classification is disabled
    if not FI_ENRICHMENT or not ENABLE_LLM_CLASSIFICATION:
        logger.debug(
            "LLM_CLASSIFICATION_DISABLED",
            fi_enrichment=FI_ENRICHMENT,
            enable_llm=ENABLE_LLM_CLASSIFICATION,
            text_preview=text[:50],
        )
        return "DESCONOCIDO"

    # Early exit if Ollama is not available
    if not is_ollama_available():
        logger.debug("LLM_UNAVAILABLE", text_preview=text[:50])
        return "DESCONOCIDO"

    # Try to use Ollama for classification
    try:
        # Build prompt with context
        prompt = f"""Clasifica el hablante del siguiente segmento de consulta médica.

Contexto previo: {context_before[:100] if context_before else "(ninguno)"}

SEGMENTO A CLASIFICAR:
{text}

Contexto siguiente: {context_after[:100] if context_after else "(ninguno)"}

Responde SOLO con una de estas palabras:
- PACIENTE (si el hablante es el paciente/patient)
- MEDICO (si el hablante es el médico/doctor/profesional)
- DESCONOCIDO (si no puedes determinar)

Respuesta (una sola palabra):"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": LLM_TEMPERATURE,
            },
            timeout=LLM_TIMEOUT_SEC,
        )

        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip().upper()

            # Parse response
            if "PACIENTE" in generated_text:
                speaker = "PACIENTE"
            elif "MEDICO" in generated_text:
                speaker = "MEDICO"
            else:
                speaker = "DESCONOCIDO"

            logger.debug("SPEAKER_CLASSIFIED", speaker=speaker, text_preview=text[:50])
            return speaker
        else:
            logger.warning(
                "LLM_CLASSIFICATION_FAILED",
                status=response.status_code,
                text_preview=text[:50],
            )
            return "DESCONOCIDO"

    except requests.Timeout:
        logger.warning("LLM_TIMEOUT", text_preview=text[:50])
        return "DESCONOCIDO"
    except Exception as e:
        logger.warning("LLM_CLASSIFICATION_ERROR", error=str(e), text_preview=text[:50])
        return "DESCONOCIDO"


def improve_text(text: str, speaker: str) -> str:
    """Apply ortografía and gramática improvements using Ollama.

    If LLM is disabled or unavailable, returns original text unchanged.

    Args:
        text: Raw transcribed text from Whisper
        speaker: Speaker role (for context-aware improvements)

    Returns:
        Improved text with better ortografía and gramática
    """
    # Early exit if LLM improvement is disabled
    if not FI_ENRICHMENT or not ENABLE_LLM_CLASSIFICATION:
        return text

    # Early exit if Ollama is not available
    if not is_ollama_available():
        return text

    # Try to improve text with Ollama
    try:
        prompt = f"""Mejora la ortografía y gramática del siguiente texto de una consulta médica.
Mantén el significado original pero corrige errores y mejora la claridad.
El hablante es un {speaker.lower()}.

TEXTO ORIGINAL:
{text}

TEXTO MEJORADO (solo el texto mejorado, sin explicaciones):"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": LLM_TEMPERATURE,
            },
            timeout=LLM_TIMEOUT_SEC,
        )

        if response.status_code == 200:
            result = response.json()
            improved = result.get("response", "").strip()
            if improved:
                logger.debug("TEXT_IMPROVED", original_len=len(text), improved_len=len(improved))
                return improved
            else:
                logger.warning("LLM_IMPROVEMENT_EMPTY", text_preview=text[:50])
                return text
        else:
            logger.warning("LLM_IMPROVEMENT_FAILED", status=response.status_code)
            return text

    except requests.Timeout:
        logger.warning("LLM_TIMEOUT_IMPROVEMENT", text_preview=text[:50])
        return text
    except Exception as e:
        logger.warning("LLM_IMPROVEMENT_ERROR", error=str(e), text_preview=text[:50])
        return text
