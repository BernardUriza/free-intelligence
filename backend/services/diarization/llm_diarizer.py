"""Claude-based diarization for medical consultations.

Uses Claude Sonnet 4.5 to intelligently segment and classify speakers in full transcripts.
(Qwen for language detection only)
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import requests

from backend.constants import (
    CLAUDE_TIMEOUT_SEC,
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_API_GENERATE_ENDPOINT,
    OLLAMA_BASE_URL as DEFAULT_OLLAMA_BASE_URL,
)
from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.services.diarization.models import DiarizationSegment
from backend.utils.text_normalizer import normalize_medical_segment

logger = get_logger(__name__)

# Ollama configuration (allow env override)
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
OLLAMA_MODEL = os.getenv("LLM_MODEL", DEFAULT_OLLAMA_MODEL)


def calculate_num_ctx(text_length: int) -> int:
    """Calculate optimal num_ctx based on text length.

    Dynamically adjusts context window to balance performance and capacity:
    - Small texts: smaller context = faster inference
    - Large texts: larger context = can handle entire document

    Args:
        text_length: Length of text in characters

    Returns:
        Optimal num_ctx value (8K to 128K)
    """
    # Estimate tokens (~4 chars per token average)
    estimated_tokens = text_length // 4

    if estimated_tokens < 4000:
        return 8192  # 8K - short texts (~30 min audio)
    elif estimated_tokens < 15000:
        return 32768  # 32K - medium texts (~2 hours audio)
    elif estimated_tokens < 30000:
        return 65536  # 64K - long texts (~4 hours audio)
    else:
        return 131072  # 128K - very long texts (>6 hours audio)


def detect_language(first_chunk_text: str) -> str:
    """Detect language of transcription using Ollama (Qwen).

    Args:
        first_chunk_text: Text from first chunk

    Returns:
        Language code: "es" or "en"
    """
    try:
        prompt = f"""Detect the language of this text. Respond with ONLY "es" (Spanish) or "en" (English).

Text: {first_chunk_text[:200]}

Language:"""

        response = requests.post(
            f"{OLLAMA_BASE_URL}{OLLAMA_API_GENERATE_ENDPOINT}",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.0,
                "options": {"num_ctx": 512},
            },
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            lang = str(result.get("response", "")).strip().lower()
            if lang in ["es", "en"]:
                logger.info("LANGUAGE_DETECTED", language=lang, method="ollama")
                return lang
    except Exception as e:
        logger.warning("LANGUAGE_DETECTION_FAILED", error=str(e))

    # Fallback: assume English
    return "en"


def diarize_with_claude(
    full_text: str,
    chunks: Optional[list[dict[str, Any]]] = None,
    webspeech_final: Optional[list[dict[str, Any]]] = None,
    language: str = "es",
) -> list[DiarizationSegment]:
    """Diarize full transcription using Claude 3.5 Sonnet with triple vision.

    Sends THREE sources to Qwen for intelligent diarization:
    1. chunks - Timestamped chunks (may have mixed speakers in one chunk)
    2. full_transcription - Complete clean text
    3. webspeech_final - Instant transcriptions (useful for natural pauses)

    This allows Qwen to:
    - Know precise timestamps from chunks
    - Segment WITHIN chunks when speaker changes mid-chunk
    - Use webspeech for natural pause detection

    Args:
        full_text: Complete transcription text
        chunks: List of chunks with timestamps [{"idx": 0, "timestamp_start": 0.0, "timestamp_end": 13.0, "text": "..."}]
        webspeech_final: WebSpeech instant transcriptions [{"timestamp": 5.2, "text": "..."}]
        language: Language code (es/en)

    Returns:
        List of DiarizationSegment objects
    """
    logger.info(
        "🎯 [DIARIZATION] Starting Claude diarization",
        text_length=len(full_text),
        chunk_count=len(chunks) if chunks else 0,
        webspeech_count=len(webspeech_final) if webspeech_final else 0,
        language=language,
        provider="claude",
    )

    # Build prompt (always in English, regardless of content language)
    logger.info("📝 [DIARIZATION] Building prompt for Claude...")
    prompt = _build_prompt(full_text, chunks, webspeech_final, language)
    logger.info(
        "✅ [DIARIZATION] Prompt built",
        prompt_length=len(prompt),
        first_100_chars=prompt[:100],
    )

    try:
        # Use llm_generate with Claude provider (model from policy: claude-sonnet-4-5-20250929)
        logger.info("🚀 [DIARIZATION] Calling Claude API (llm_generate)...")
        logger.info("⏳ [DIARIZATION] Waiting for Claude response (this may take 10-30 seconds)...")

        response = llm_generate(
            prompt,
            provider="claude",
            max_tokens=8192,
            temperature=0.3,  # Balanced between deterministic and creative
        )

        logger.info("✅ [DIARIZATION] Claude API response received")
        generated_text = response.content.strip()

        logger.info(
            "📄 [DIARIZATION] Raw response preview",
            response_length=len(generated_text),
            first_500_chars=generated_text[:500],
        )

        # Parse JSON response
        logger.info("🔍 [DIARIZATION] Parsing JSON response...")
        segments = _parse_response(generated_text, full_text, chunks)

        logger.info(
            "✅ [DIARIZATION] SUCCESS - Diarization complete",
            segment_count=len(segments),
            provider="claude",
        )
        return segments

    except Exception as e:
        logger.error(
            "❌ [DIARIZATION] FATAL ERROR during Claude diarization",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        logger.info("🔄 [DIARIZATION] Falling back to DESCONOCIDO segment...")
        return _fallback_segments(full_text)


def _build_prompt(
    full_text: str,
    chunks: Optional[list[dict[str, Any]]] = None,
    webspeech_final: Optional[list[dict[str, Any]]] = None,
    content_language: str = "en",
) -> str:
    """Build English prompt for Claude with triple vision.

    Prompt is ALWAYS in English, regardless of content language.
    """
    # Build triple vision JSON
    triple_vision: dict[str, Any] = {"full_transcription": full_text}

    if chunks:
        # Format chunks with timestamps + first words (temporal anchors)
        chunk_list = []
        for chunk in chunks:
            text = chunk.get("transcript", "")
            # Get first ~10-15 words as temporal anchor
            words = text.split()[:15]
            first_words = " ".join(words) + ("..." if len(text.split()) > 15 else "")

            chunk_list.append(
                {
                    "idx": chunk.get("chunk_number", chunk.get("idx", 0)),
                    "time": f"{chunk.get('timestamp_start', 0):.1f}-{chunk.get('timestamp_end', 0):.1f}s",
                    "starts_with": first_words,
                }
            )
        triple_vision["chunks_timestamps"] = chunk_list

    if webspeech_final:
        # Format webspeech with timestamps
        ws_list = []
        for ws in webspeech_final:
            ws_list.append(
                {
                    "time": f"{ws.get('timestamp', 0):.1f}s",
                    "text": ws.get("text", ""),
                }
            )
        triple_vision["webspeech_final"] = ws_list

    triple_vision_json = json.dumps(triple_vision, ensure_ascii=False, indent=2)

    # Language-specific note and example
    if content_language == "es":
        lang_note = "in Spanish"
        example_input = "hola buenas tardes maria cómo ves a todos que tenías la semana pasada mucho mejor doctor pero ahora tengo la voz ronca"
        example_output = """{{
  "segments": [
    {{"speaker": "MEDICO", "text": "Hola, buenas tardes María. ¿Cómo ves a todos que tenías la semana pasada?", "timestamp_start": 0.0, "timestamp_end": 5.2}},
    {{"speaker": "PACIENTE", "text": "Mucho mejor, doctor, pero ahora tengo la voz ronca.", "timestamp_start": 5.2, "timestamp_end": 9.8}}
  ]
}}"""
    else:
        lang_note = "in English"
        example_input = "come in miss bellamy yes hi can you tell me why you're here today i have a terrible headache"
        example_output = """{{
  "segments": [
    {{"speaker": "MEDICO", "text": "Come in. Miss Bellamy?", "timestamp_start": 0.0, "timestamp_end": 2.1}},
    {{"speaker": "PACIENTE", "text": "Yes.", "timestamp_start": 2.1, "timestamp_end": 2.5}},
    {{"speaker": "MEDICO", "text": "Hi. Can you tell me why you're here today?", "timestamp_start": 2.5, "timestamp_end": 5.0}},
    {{"speaker": "PACIENTE", "text": "I have a terrible headache.", "timestamp_start": 5.0, "timestamp_end": 7.2}}
  ]
}}"""

    # Few-shot example based on DiarizationLM research (prompt ALWAYS in English)
    return f"""You are a medical assistant expert in speaker classification and medical transcription normalization. Your task is to IDENTIFY who is speaking in each conversation turn AND properly format the text with correct punctuation and capitalization.

NOTE: The transcript content is {lang_note}, but you must classify speakers using the labels "MEDICO" and "PACIENTE" regardless.

APPROACH (based on DiarizationLM 2024 research):
Instead of segmenting from scratch, use chunks_timestamps as TEMPORAL REFERENCE to know which words occur at which approximate time.

EXPECTED FORMAT EXAMPLE ({lang_note}):
Input (raw transcription without punctuation):
  full_transcription: "{example_input}"

Correct output (with proper punctuation, capitalization, AND timestamps):
{example_output}

IMPORTANT: You MUST include timestamp_start and timestamp_end for each segment based on the chunks_timestamps data.
Use the chunk timestamps to estimate when each speaker turn occurs in the audio.

INSTRUCTIONS:
1. USE chunks_timestamps to know WHICH WORDS occur at WHICH TIME (first words of each chunk give you temporal anchor)
2. IDENTIFY each conversation turn (one turn = one person speaks without interruption)
3. CLASSIFY each turn:
   - MEDICO: Doctor/health professional (asks medical questions, gives diagnosis)
   - PACIENTE: Patient (describes symptoms, answers questions)
4. Create ONE segment per EACH turn (don't group multiple turns together)
5. NORMALIZE text for medical documentation:
   - Add proper capitalization:
     * ALWAYS capitalize first word of each segment
     * Capitalize after periods (. ), question marks (? ), exclamation marks (! )
     * Capitalize proper nouns (María, José, Dr. García)
     * Use LOWERCASE for common articles/prepositions mid-sentence (el, la, de, en, con)
   - Add punctuation (periods, commas, question marks, exclamation marks)
   - Fix obvious spelling/grammar errors
   - Preserve medical terminology accuracy
   - Keep the original meaning and words (don't paraphrase or change medical content)

CAPITALIZATION EXAMPLES (CRITICAL):
❌ Wrong: "hola buenos días" → ✅ Correct: "Hola, buenos días."
❌ Wrong: "el dolor Es fuerte" → ✅ Correct: "El dolor es fuerte."
❌ Wrong: "muy bien Doctor" → ✅ Correct: "Muy bien, doctor."

INPUT DATA:
{triple_vision_json}

RESPOND ONLY WITH THE JSON (no explanations):"""


def _parse_response(
    response_text: str,
    original_text: str,
    chunks: Optional[list[dict[str, Any]]] = None,
) -> list[DiarizationSegment]:
    """Parse Qwen's JSON response into DiarizationSegments with accurate timestamps.

    Args:
        response_text: Qwen's generated text (should be JSON)
        original_text: Original transcript (for fallback)
        chunks: List of chunks with real timestamps (for accurate timing)

    Returns:
        List of DiarizationSegment objects with accurate timestamps
    """
    try:
        # Extract JSON from response (Qwen might add extra text)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            logger.warning("NO_JSON_FOUND", response_preview=response_text[:200])
            return _fallback_segments(original_text)

        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)

        segments_data = data.get("segments", [])

        if not segments_data:
            logger.warning("EMPTY_SEGMENTS", data=data)
            return _fallback_segments(original_text)

        # Calculate total audio duration from chunks (for validation)
        total_duration = 0.0
        if chunks:
            total_duration = max(chunk.get("timestamp_end", 0) for chunk in chunks)
            logger.info(f"📏 [DIARIZATION] Total audio duration from chunks: {total_duration:.1f}s")

        # Convert to DiarizationSegment objects using LLM-provided timestamps
        segments = []
        cumulative_time = 0.0  # For fallback only

        for seg_data in segments_data:
            speaker = seg_data.get("speaker", "DESCONOCIDO").upper()
            text = seg_data.get("text", "")

            if not text:
                continue

            # Apply post-processing normalization (capitalization fix)
            text = normalize_medical_segment(text)

            # TRY to get timestamps from LLM response (GPT-4 has the power!)
            start_time = seg_data.get("timestamp_start")
            end_time = seg_data.get("timestamp_end")

            # Fallback: if LLM didn't provide timestamps, calculate proportionally
            if start_time is None or end_time is None:
                logger.warning(
                    "LLM_MISSING_TIMESTAMPS",
                    segment_idx=len(segments),
                    falling_back=True,
                )
                # Calculate total text length for proportional distribution
                total_text_length = sum(len(s.get("text", "")) for s in segments_data)

                if chunks and total_duration > 0 and total_text_length > 0:
                    # Proportional distribution based on actual audio duration
                    text_ratio = len(text) / total_text_length
                    duration = total_duration * text_ratio
                else:
                    # Last resort: rough heuristic
                    duration = len(text) / 12.5

                start_time = cumulative_time
                end_time = start_time + duration
                cumulative_time = end_time

            segment = DiarizationSegment(
                start_time=float(start_time),
                end_time=float(end_time),
                speaker=speaker,
                text=text,
            )
            segments.append(segment)

        final_duration = segments[-1].end_time if segments else 0.0
        logger.info(
            "SEGMENTS_PARSED",
            count=len(segments),
            final_timestamp=f"{final_duration:.1f}s",
            chunks_duration=f"{total_duration:.1f}s" if chunks else "N/A",
            timestamp_source="LLM"
            if segments and segments[0].start_time is not None
            else "fallback",
        )
        return segments

    except json.JSONDecodeError as e:
        logger.error("JSON_PARSE_ERROR", error=str(e), response_preview=response_text[:500])
        return _fallback_segments(original_text)
    except Exception as e:
        logger.error("PARSE_ERROR", error=str(e), exc_info=True)
        return _fallback_segments(original_text)


def _fallback_segments(full_text: str) -> list[DiarizationSegment]:
    """Fallback: return single DESCONOCIDO segment."""
    logger.warning("USING_FALLBACK_SEGMENT", text_length=len(full_text))

    return [
        DiarizationSegment(
            start_time=0.0,
            end_time=len(full_text) / 12.5,  # Rough estimate
            speaker="DESCONOCIDO",
            text=full_text,
        )
    ]
