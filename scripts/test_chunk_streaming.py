#!/usr/bin/env python3
"""
Test Chunk Streaming - Simula RecordRTC enviando chunks

Usage:
    python3 scripts/test_chunk_streaming.py <audio.mp3>

Divide el audio en chunks de 3s y los envía secuencialmente
para probar el endpoint /stream con polling real.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

CHUNK_DURATION = 3  # seconds
API_BASE = "http://localhost:7001/api/workflows/aurity"


def split_audio(input_file: Path, output_dir: Path) -> list[Path]:
    """Divide audio en chunks de 3s usando ffmpeg."""
    print(f"🔪 Dividiendo {input_file.name} en chunks de {CHUNK_DURATION}s...")

    # ffmpeg -i input.mp3 -f segment -segment_time 3 -c copy output_%03d.mp3
    cmd = [
        "ffmpeg",
        "-i",
        str(input_file),
        "-f",
        "segment",
        "-segment_time",
        str(CHUNK_DURATION),
        "-c",
        "copy",
        str(output_dir / "chunk_%03d.mp3"),
        "-y",
        "-loglevel",
        "error",
    ]

    subprocess.run(cmd, check=True)

    chunks = sorted(output_dir.glob("chunk_*.mp3"))
    print(f"✅ {len(chunks)} chunks creados\n")
    return chunks


def send_chunk(session_id: str, chunk_number: int, chunk_file: Path) -> str:
    """Envía chunk y devuelve job_id."""
    print(f"📤 Chunk {chunk_number}: {chunk_file.name} ({chunk_file.stat().st_size} bytes)")

    with open(chunk_file, "rb") as f:
        files = {"audio": f}
        data = {"session_id": session_id, "chunk_number": chunk_number}

        response = requests.post(f"{API_BASE}/stream", files=files, data=data)
        response.raise_for_status()

        result = response.json()
        job_id: str = result["job_id"]
        print(f"   ✓ job_id: {job_id}")
        return job_id


def poll_job(job_id: str, max_attempts: int = 20, delay: float = 0.5) -> dict[str, object]:
    """Poll job hasta que complete o falle."""
    for _ in range(max_attempts):
        response = requests.get(f"{API_BASE}/jobs/{job_id}")

        if response.status_code == 404:
            print("   ⚠️  Job no encontrado (404)")
            return {"status": "not_found"}

        result = response.json()
        status = result["status"]

        if status == "completed":
            transcript = result.get("transcript", "")
            latency = result.get("latency_ms", 0)
            print(f'   ✅ Completado ({latency}ms): "{transcript[:60]}..."')
            return result
        elif status == "failed":
            error = result.get("error", "Unknown")
            print(f"   ❌ Falló: {error}")
            return result

        time.sleep(delay)

    print(f"   ⏱️  Timeout después de {max_attempts * delay}s")
    return {"status": "timeout"}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/test_chunk_streaming.py <audio.mp3>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        sys.exit(1)

    session_id = f"test_streaming_{int(time.time())}"
    print(f"🎬 Session: {session_id}")
    print(f"📁 Input: {input_file}\n")

    # Create temp dir for chunks
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Split audio
        chunks = split_audio(input_file, output_dir)

        # Send chunks sequentially
        print("🚀 Enviando chunks...\n")
        results = []

        for i, chunk_file in enumerate(chunks):
            job_id = send_chunk(session_id, i, chunk_file)
            result = poll_job(job_id)
            results.append(result)
            print()

            # Delay between chunks (simulate recording)
            if i < len(chunks) - 1:
                time.sleep(0.5)

        # Summary
        print("=" * 60)
        print("📊 RESUMEN")
        print("=" * 60)

        completed = [r for r in results if r.get("status") == "completed"]
        failed = [r for r in results if r.get("status") == "failed"]

        print(f"Total chunks: {len(chunks)}")
        print(f"Completados:  {len(completed)}")
        print(f"Fallados:     {len(failed)}")
        print()

        if completed:
            total_transcript = " ".join(
                r.get("transcript", "") for r in completed if r.get("transcript")
            )
            avg_latency = sum(r.get("latency_ms", 0) for r in completed) / len(completed)

            print(f"Latencia promedio: {avg_latency:.0f}ms")
            print(f"\n📝 Transcript completo ({len(total_transcript)} chars):")
            print(f"   {total_transcript}\n")


if __name__ == "__main__":
    main()
