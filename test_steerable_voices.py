#!/usr/bin/env python3
"""
Test OpenAI Steerable TTS with Mexican Spanish accent
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.services.tts_openai_steerable import get_steerable_tts_service


async def main():
    """Generate greetings with Mexican Spanish accent"""
    tts = get_steerable_tts_service()

    # Test with the 3 available steerable voices
    voices = ["alloy", "echo", "shimmer"]

    for voice in voices:
        print(f"\n🎙️ Generating {voice} with Mexican Spanish accent...")

        text = f"Hola, soy {voice}. Hablo español mexicano de forma natural."

        try:
            audio = await tts.synthesize(
                text=text, voice=voice, accent="Mexican Spanish", response_format="mp3", speed=1.0
            )

            # Save to temp file
            output_file = f"/tmp/steerable_{voice}.mp3"
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
