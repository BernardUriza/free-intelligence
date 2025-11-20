#!/usr/bin/env python3
"""Poll transcription session progress every 15 seconds.

Monitors transcription job progress via /api/internal/transcribe/jobs/{session_id}

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: FI-STRIDE polling automation
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

# ============================================================================
# Configuration
# ============================================================================

API_BASE = "http://localhost:7001"
SESSION_ID_FILE = Path("/tmp/patient_session_id.txt")
POLL_INTERVAL_SECONDS = 15
TIMEOUT_MINUTES = 20
MAX_TRANSCRIPT_PREVIEW = 500


# ============================================================================
# Data Models
# ============================================================================


class TranscriptionStatus:
    """Transcription job status."""

    def __init__(self, data: dict):
        self.session_id: str = data["session_id"]
        self.job_id: str = data["job_id"]
        self.status: str = data["status"]
        self.total_chunks: int = data["total_chunks"]
        self.processed_chunks: int = data["processed_chunks"]
        self.progress_percent: int = data["progress_percent"]
        self.chunks: list[dict] = data.get("chunks", [])
        self.created_at: str = data["created_at"]
        self.updated_at: str = data["updated_at"]

    def is_complete(self) -> bool:
        """Check if job is complete."""
        return self.status == "completed" or self.progress_percent >= 100

    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == "failed"

    def get_full_transcript(self) -> str:
        """Get concatenated transcript from all chunks."""
        sorted_chunks = sorted(self.chunks, key=lambda c: c["chunk_number"])
        return " ".join(
            chunk.get("transcript", "") for chunk in sorted_chunks if chunk.get("transcript")
        )


# ============================================================================
# Core Functions
# ============================================================================


def wait_for_session_id_file(timeout_seconds: int = 300) -> str | None:
    """Wait for session_id file to exist and read it.

    Args:
        timeout_seconds: Max time to wait (default 5 minutes)

    Returns:
        session_id or None if timeout
    """
    print(f"⏳ Waiting for session ID file: {SESSION_ID_FILE}")
    start = datetime.now(UTC)
    deadline = start + timedelta(seconds=timeout_seconds)

    while datetime.now(UTC) < deadline:
        if SESSION_ID_FILE.exists():
            session_id = SESSION_ID_FILE.read_text().strip()
            print(f"✅ Found session ID: {session_id}")
            return session_id

        time.sleep(2)

    print(f"❌ Timeout waiting for {SESSION_ID_FILE}")
    return None


def get_transcription_status(session_id: str) -> TranscriptionStatus | None:
    """Fetch transcription job status.

    Args:
        session_id: Session UUID

    Returns:
        TranscriptionStatus or None if error
    """
    url = f"{API_BASE}/api/internal/transcribe/jobs/{session_id}"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return TranscriptionStatus(data)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"⚠️  Job not found yet for session {session_id}")
            return None
        print(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        return None

    except Exception as e:
        print(f"❌ Error fetching status: {e}")
        return None


def format_timestamp() -> str:
    """Get formatted timestamp HH:MM:SS."""
    return datetime.now(UTC).strftime("%H:%M:%S")


def poll_until_complete(session_id: str) -> TranscriptionStatus | None:
    """Poll transcription status every 15 seconds.

    Args:
        session_id: Session UUID

    Returns:
        Final TranscriptionStatus or None if timeout/error
    """
    start_time = datetime.now(UTC)
    deadline = start_time + timedelta(minutes=TIMEOUT_MINUTES)

    print(
        f"\n🔄 Starting polling (interval: {POLL_INTERVAL_SECONDS}s, timeout: {TIMEOUT_MINUTES}min)"
    )
    print("=" * 80)

    while datetime.now(UTC) < deadline:
        status = get_transcription_status(session_id)

        if status:
            # Format progress line
            timestamp = format_timestamp()
            chunks_str = f"{status.processed_chunks}/{status.total_chunks}"
            print(
                f"[{timestamp}] Session: {session_id[:12]}... | "
                f"Progress: {status.progress_percent}% | "
                f"Chunks: {chunks_str} | "
                f"Status: {status.status}"
            )

            # Check completion
            if status.is_complete():
                elapsed = datetime.now(UTC) - start_time
                print("=" * 80)
                print(f"✅ COMPLETED in {elapsed.total_seconds():.1f}s")
                return status

            if status.is_failed():
                elapsed = datetime.now(UTC) - start_time
                print("=" * 80)
                print(f"❌ FAILED after {elapsed.total_seconds():.1f}s")
                return status

        # Wait before next poll
        time.sleep(POLL_INTERVAL_SECONDS)

    # Timeout
    elapsed = datetime.now(UTC) - start_time
    print("=" * 80)
    print(f"⏰ TIMEOUT after {elapsed.total_seconds():.1f}s ({TIMEOUT_MINUTES} minutes)")

    # Get final status
    return get_transcription_status(session_id)


def print_final_report(status: TranscriptionStatus | None, elapsed_seconds: float) -> None:
    """Print final report.

    Args:
        status: Final transcription status
        elapsed_seconds: Total elapsed time
    """
    print("\n" + "=" * 80)
    print("FINAL REPORT")
    print("=" * 80)

    if not status:
        print("❌ No status available")
        return

    print(f"Session ID:        {status.session_id}")
    print(f"Final Status:      {status.status}")
    print(f"Total Time:        {elapsed_seconds:.1f}s ({elapsed_seconds / 60:.1f}min)")
    print(f"Final Chunks:      {status.processed_chunks}/{status.total_chunks}")
    print(f"Progress:          {status.progress_percent}%")
    print(f"Created At:        {status.created_at}")
    print(f"Updated At:        {status.updated_at}")

    # Transcript preview
    if status.chunks:
        full_transcript = status.get_full_transcript()
        preview = full_transcript[:MAX_TRANSCRIPT_PREVIEW]

        print(f"\nTranscript Preview ({len(full_transcript)} total chars):")
        print("-" * 80)
        print(preview)
        if len(full_transcript) > MAX_TRANSCRIPT_PREVIEW:
            print(f"... ({len(full_transcript) - MAX_TRANSCRIPT_PREVIEW} more characters)")
        print("-" * 80)
    else:
        print("\n⚠️  No transcript available")

    print("=" * 80)


# ============================================================================
# Main
# ============================================================================


def main() -> int:
    """Main entry point.

    Returns:
        0 on success, 1 on error
    """
    print("🚀 Transcription Progress Polling Agent")
    print(f"API Base: {API_BASE}")
    print(f"Session ID File: {SESSION_ID_FILE}")
    print()

    # 1. Wait for session ID file
    session_id = wait_for_session_id_file()
    if not session_id:
        return 1

    # 2. Poll until complete
    start_time = datetime.now(UTC)
    final_status = poll_until_complete(session_id)
    elapsed = (datetime.now(UTC) - start_time).total_seconds()

    # 3. Print final report
    print_final_report(final_status, elapsed)

    # 4. Exit code
    if final_status and final_status.is_complete():
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
