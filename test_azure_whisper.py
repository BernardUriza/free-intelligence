"""Test Azure Whisper directamente."""
import sys
sys.path.insert(0, '/Users/bernardurizaorozco/Documents/free-intelligence')

from backend.providers.stt import get_stt_provider

audio_file = "/Users/bernardurizaorozco/Desktop/Patient-Centered Chunks/chunk_001.mp3"

print(f"🔍 Testing Azure Whisper with: {audio_file}")

try:
    # Force Azure Whisper
    provider = get_stt_provider("azure_whisper", config={
        "enabled": True,
        "timeout_seconds": 30,
        "model": "whisper-1"
    })

    print(f"✅ Provider created: {provider}")
    print(f"🎙️  Starting transcription...")

    response = provider.transcribe(audio_file, language="es")

    print(f"\n✅ SUCCESS!")
    print(f"📝 Transcript: {response.text}")
    print(f"⏱️  Duration: {response.duration}s")
    print(f"🎯 Confidence: {response.confidence}")
    print(f"📊 Provider: {response.provider}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
