#!/usr/bin/env python3
"""
Test Unified TTS with auto-detection
"""

import asyncio

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.services.tts.services.tts_unified import get_unified_tts_service


async def main():
    """Test auto-detection of steerable TTS for Spanish text"""
    tts = get_unified_tts_service()

    tests = [
        {
            "text": "Hola, buenos días. ¿Cómo se encuentra hoy?",
            "voice": "alloy",
            "provider": None,  # Should auto-detect openai-steerable
            "desc": "Spanish text + steerable voice → should use openai-steerable",
        },
        {
            "text": "Hello, good morning. How are you today?",
            "voice": "alloy",
            "provider": None,  # Should use standard openai
            "desc": "English text + steerable voice → should use openai standard",
        },
        {
            "text": "Hola, soy una voz nativa mexicana",
            "voice": "nova",
            "provider": None,  # Should use openai-steerable (Spanish auto-detect)
            "desc": "Spanish text + nova voice → should use openai-steerable",
        },
    ]

    for i, test in enumerate(tests, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}: {test['desc']}")
        print(f"Text: {test['text'][:50]}...")
        print(f"Voice: {test['voice']}")
        print(f"Provider: {test['provider']}")
        print(f"{'=' * 70}")

        try:
            audio = await tts.synthesize(
                text=test["text"],
                voice=test["voice"],
                provider=test["provider"],
                response_format="mp3",
                speed=1.0,
            )

            # Save to temp file
            output_file = f"/tmp/test_{i}.mp3"
            with open(output_file, "wb") as f:
                f.write(audio)

            print(f"✅ Generated {len(audio) / 1024:.1f}KB → {output_file}")
            print("   Playing...")

            # Play using afplay
            os.system(f"afplay {output_file}")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
