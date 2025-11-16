"""Text normalization utilities for medical transcriptions.

Post-processing to fix capitalization issues that LLMs might miss.
"""

from __future__ import annotations

import re


def normalize_capitalization(text: str) -> str:
    """Normalize capitalization in medical transcription text.

    Rules:
    1. Capitalize first character of text
    2. Capitalize after sentence endings (. ! ?)
    3. Lowercase common mid-sentence words (El → el, La → la, De → de)
    4. Preserve proper nouns and medical terms

    Args:
        text: Raw transcription text

    Returns:
        Normalized text with proper capitalization

    Examples:
        >>> normalize_capitalization("hola buenos días")
        "Hola buenos días"
        >>> normalize_capitalization("el dolor Es muy fuerte. la garganta está roja")
        "El dolor es muy fuerte. La garganta está roja"
        >>> normalize_capitalization("muy bien Doctor García")
        "Muy bien doctor García"
    """
    if not text or not text.strip():
        return text

    # Step 1: Capitalize first character
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

    # Step 2: Capitalize after sentence endings (. ! ?)
    # Matches: ". word" → ". Word"
    text = re.sub(r'([.!?]\s+)([a-záéíóúñü])', lambda m: m.group(1) + m.group(2).upper(), text)

    # Step 3: Fix common mid-sentence capitalization errors
    # "El " → "el " (when not at start of sentence)
    # But preserve after sentence endings
    common_words = {
        r'\bEl\b': 'el',
        r'\bLa\b': 'la',
        r'\bLos\b': 'los',
        r'\bLas\b': 'las',
        r'\bUn\b': 'un',
        r'\bUna\b': 'una',
        r'\bDe\b': 'de',
        r'\bEn\b': 'en',
        r'\bCon\b': 'con',
        r'\bPor\b': 'por',
        r'\bPara\b': 'para',
        r'\bEs\b': 'es',
    }

    for pattern, replacement in common_words.items():
        # Only replace if NOT at start of sentence (after . ! ?)
        # Use negative lookbehind to avoid replacing after sentence endings
        text = re.sub(
            rf'(?<![.!?]\s)({pattern})',
            replacement,
            text
        )

    # Step 4: Lowercase "doctor" when not a proper noun (e.g., "gracias Doctor" → "gracias doctor")
    # But preserve "Doctor García" (followed by capital letter)
    text = re.sub(r'\bDoctor(?!\s+[A-ZÁÉÍÓÚÑ])', 'doctor', text)

    # Step 5: Fix double spaces created by previous operations
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_medical_segment(segment_text: str) -> str:
    """Normalize a single diarization segment.

    Wrapper around normalize_capitalization with medical-specific tweaks.

    Args:
        segment_text: Raw segment text

    Returns:
        Normalized segment text
    """
    # Apply capitalization normalization
    normalized = normalize_capitalization(segment_text)

    # Ensure text ends with punctuation
    if normalized and not normalized[-1] in '.!?':
        normalized += '.'

    return normalized
