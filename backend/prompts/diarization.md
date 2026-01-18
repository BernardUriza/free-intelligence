# Diarization Prompt

Analyze this medical consultation transcript and identify speakers.

## Transcript

{transcript}

## Instructions

1. Identify each speaker (typically Doctor and Patient)
2. Split the transcript into segments by speaker
3. For each segment, provide:
   - speaker: "Doctor" or "Patient"
   - text: The exact text spoken
   - improved_text: Cleaned/corrected version (fix typos, add punctuation)

## Output Format

Return JSON array:

```json
[
  {"speaker": "Doctor", "text": "...", "improved_text": "..."},
  {"speaker": "Patient", "text": "...", "improved_text": "..."}
]
```

Only return the JSON array, no other text.
