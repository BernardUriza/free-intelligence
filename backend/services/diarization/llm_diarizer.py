"""Claude-based diarization for medical consultations.

Uses Claude Sonnet 4.5 to intelligently segment and classify speakers in full transcripts.
(Qwen for language detection only)
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from backend.logger import get_logger
from backend.providers.llm import llm_generate
from backend.services.diarization.models import DiarizationSegment

logger = get_logger(__name__)

# Ollama for language detection
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct-q4_0")

# Claude for diarization (demo mode) - using existing adapter
CLAUDE_TIMEOUT_SEC = 60.0  # Claude is faster than Qwen


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
            f"{OLLAMA_BASE_URL}/api/generate",
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
            lang = result.get("response", "").strip().lower()
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
    # Calculate optimal num_ctx based on text length
    num_ctx = calculate_num_ctx(len(full_text))

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
        segments = _parse_response(generated_text, full_text)

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
    triple_vision = {"full_transcription": full_text}

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

    # Language-specific note
    lang_note = "in Spanish" if content_language == "es" else "in English"

    # Few-shot example based on DiarizationLM research (prompt ALWAYS in English)
    return f"""You are a medical assistant expert in speaker classification. Your task is to IDENTIFY who is speaking in each conversation turn.

NOTE: The transcript content is {lang_note}, but you must classify speakers using the labels "MEDICO" and "PACIENTE" regardless.

APPROACH (based on DiarizationLM 2024 research):
Instead of segmenting from scratch, use chunks_timestamps as TEMPORAL REFERENCE to know which words occur at which approximate time.

EXPECTED FORMAT EXAMPLE:
Input:
  full_transcription: "Come in. Miss Bellamy? Yes. Hi. Can you tell me why you're here today? I have a terrible headache."
  chunks_timestamps: [{{"time": "0.0-15.0s", "starts_with": "Come in. Miss Bellamy? Yes..."}}]

Correct output:
{{
  "segments": [
    {{"speaker": "MEDICO", "text": "Come in. Miss Bellamy?"}},
    {{"speaker": "PACIENTE", "text": "Yes."}},
    {{"speaker": "MEDICO", "text": "Hi."}},
    {{"speaker": "MEDICO", "text": "Can you tell me why you're here today?"}},
    {{"speaker": "PACIENTE", "text": "I have a terrible headache."}}
  ]
}}

INSTRUCTIONS:
1. USE chunks_timestamps to know WHICH WORDS occur at WHICH TIME (first words of each chunk give you temporal anchor)
2. IDENTIFY each conversation turn (one turn = one person speaks without interruption)
3. CLASSIFY each turn:
   - MEDICO: Doctor/health professional (asks medical questions, gives diagnosis)
   - PACIENTE: Patient (describes symptoms, answers questions)
4. Create ONE segment per EACH turn (don't group multiple turns together)
5. RESPECT exact text (don't modify words)

INPUT DATA:
{triple_vision_json}

RESPOND ONLY WITH THE JSON (no explanations):"""


def _parse_response(response_text: str, original_text: str) -> list[DiarizationSegment]:
    """Parse Qwen's JSON response into DiarizationSegments.

    Args:
        response_text: Qwen's generated text (should be JSON)
        original_text: Original transcript (for fallback)

    Returns:
        List of DiarizationSegment objects
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

        # Convert to DiarizationSegment objects
        segments = []
        cumulative_time = 0.0

        for seg_data in segments_data:
            speaker = seg_data.get("speaker", "DESCONOCIDO").upper()
            text = seg_data.get("text", "")

            if not text:
                continue

            # Estimate duration based on text length (rough heuristic)
            # Assume ~150 words per minute, ~5 chars per word = 750 chars/min = 12.5 chars/sec
            duration = len(text) / 12.5
            start_time = cumulative_time
            end_time = start_time + duration

            segment = DiarizationSegment(
                start_time=start_time,
                end_time=end_time,
                speaker=speaker,
                text=text,
            )
            segments.append(segment)

            cumulative_time = end_time

        logger.info("SEGMENTS_PARSED", count=len(segments))
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
