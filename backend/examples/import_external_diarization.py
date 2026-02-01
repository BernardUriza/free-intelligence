"""Example: Import pre-diarized transcript from external service (e.g., Cue.ai).

This demonstrates how to use the /sessions/{id}/diarization/import endpoint
to import speaker-separated transcripts from external diarization services,
avoiding the need to re-process audio.

Use cases:
- Cue.ai pre-diarized transcripts
- AssemblyAI speaker diarization
- Manual transcription with speaker labels
- Any external service providing speaker-separated text

Author: Claude Code
Created: 2026-01-27
"""

import requests
import json
from typing import Any

# Example diarization data from external service (e.g., Cue.ai)
external_diarization_data = {
    "segments": [
        {
            "start_time": 0.0,
            "end_time": 5.2,
            "speaker": {
                "speaker_id": "DOCTOR",
                "name": "Dr. García",
                "confidence": 0.95
            },
            "text": "Buenas tardes, ¿cómo se encuentra hoy?",
            "confidence": 0.92
        },
        {
            "start_time": 5.5,
            "end_time": 8.3,
            "speaker": {
                "speaker_id": "PATIENT",
                "name": "Paciente",
                "confidence": 0.88
            },
            "text": "Buenas tardes doctor, me duele mucho la cabeza desde ayer.",
            "confidence": 0.85
        },
        {
            "start_time": 8.5,
            "end_time": 12.7,
            "speaker": {
                "speaker_id": "DOCTOR",
                "name": "Dr. García",
                "confidence": 0.95
            },
            "text": "Entiendo. ¿El dolor es constante o viene y va?",
            "confidence": 0.90
        },
        {
            "start_time": 13.0,
            "end_time": 18.2,
            "speaker": {
                "speaker_id": "PATIENT",
                "name": "Paciente",
                "confidence": 0.88
            },
            "text": "Es constante, y cuando me muevo mucho se pone peor. También me dan náuseas.",
            "confidence": 0.87
        },
        {
            "start_time": 18.5,
            "end_time": 25.8,
            "speaker": {
                "speaker_id": "DOCTOR",
                "name": "Dr. García",
                "confidence": 0.95
            },
            "text": "De acuerdo. Voy a revisar su presión arterial y hacerle algunas preguntas más.",
            "confidence": 0.93
        }
    ],
    "provider": "cue",
    "metadata": {
        "language": "es-MX",
        "audio_duration": 25.8,
        "external_job_id": "cue-12345",
        "processing_time_ms": 1234
    }
}


def import_external_diarization(
    session_id: str,
    diarization_data: dict[str, Any],
    backend_url: str = "http://localhost:7001"
) -> dict[str, Any]:
    """Import external diarization to Free Intelligence backend.

    Args:
        session_id: Session UUID
        diarization_data: Dict with segments, provider, metadata
        backend_url: Backend API URL (default: localhost:7001)

    Returns:
        Response dict with import status
    """
    url = f"{backend_url}/api/workflows/aurity/sessions/{session_id}/diarization/import"

    response = requests.post(url, json=diarization_data)

    if response.status_code == 201:
        print("✅ External diarization imported successfully!")
        result = response.json()
        print(f"   Provider: {result['provider']}")
        print(f"   Segments imported: {result['segments_imported']}")
        print(f"   Speakers identified: {result['speakers_identified']}")
        print(f"   Duration: {result['duration_seconds']:.1f}s")
        print(f"   Speakers:")
        for speaker in result['speakers']:
            print(f"     - {speaker['speaker_id']}: {speaker['name']} (confidence: {speaker['confidence']:.2f})")
        return result
    else:
        print(f"❌ Import failed: {response.status_code}")
        print(f"   {response.text}")
        response.raise_for_status()


def example_cue_integration():
    """Example: Integrate with Cue.ai diarization service."""
    # Step 1: User records audio in Aurity frontend
    session_id = "550e8400-e29b-41d4-a716-446655440000"  # Replace with actual session ID

    # Step 2: Send audio to Cue.ai for diarization (not shown here)
    # cue_response = cue_client.diarize_audio(audio_file)

    # Step 3: Transform Cue.ai response to Free Intelligence format
    # (Assuming external_diarization_data above came from Cue.ai)

    # Step 4: Import to Free Intelligence
    result = import_external_diarization(session_id, external_diarization_data)

    # Step 5: Now you can generate SOAP note from imported diarization
    # POST /sessions/{session_id}/soap
    print("\n📝 Next step: Generate SOAP note with:")
    print(f"   POST /api/workflows/aurity/sessions/{session_id}/soap")


def example_manual_transcript():
    """Example: Import manually transcribed conversation with speaker labels."""
    session_id = "660e8400-e29b-41d4-a716-446655440001"

    manual_transcript = {
        "segments": [
            {
                "start_time": 0.0,
                "end_time": 5.0,
                "speaker": {"speaker_id": "DOCTOR", "name": "Dra. López"},
                "text": "Buenos días, ¿cómo te sientes hoy?",
                "confidence": 1.0  # Manual transcription = high confidence
            },
            {
                "start_time": 5.0,
                "end_time": 10.0,
                "speaker": {"speaker_id": "PATIENT", "name": "María Rodríguez"},
                "text": "Buenos días doctora, me duele la garganta y tengo tos.",
                "confidence": 1.0
            }
        ],
        "provider": "manual",
        "metadata": {"transcriber": "Medical Assistant", "language": "es-MX"}
    }

    result = import_external_diarization(session_id, manual_transcript)
    print(f"\n✅ Manual transcript imported for session {session_id}")


if __name__ == "__main__":
    print("=" * 60)
    print("FREE INTELLIGENCE - External Diarization Import Examples")
    print("=" * 60)

    print("\n1️⃣  Example: Cue.ai Integration")
    print("-" * 60)
    try:
        example_cue_integration()
    except Exception as e:
        print(f"⚠️  Example failed (expected if backend not running): {e}")

    print("\n2️⃣  Example: Manual Transcript")
    print("-" * 60)
    try:
        example_manual_transcript()
    except Exception as e:
        print(f"⚠️  Example failed (expected if backend not running): {e}")

    print("\n" + "=" * 60)
    print("📖 For more info, see:")
    print("   - API docs: http://localhost:7001/docs")
    print("   - Endpoint: POST /api/workflows/aurity/sessions/{id}/diarization/import")
    print("=" * 60)
