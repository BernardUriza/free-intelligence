#!/usr/bin/env python3
"""Test concurrent HDF5 writes with session-level architecture.

This test simulates the production scenario where 4 workers write to HDF5
simultaneously, verifying zero concurrency conflicts.

Expected result: All 4 workers complete successfully without corruption.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.models.task_type import TaskType
from backend.src.fi_common.logging.logger import get_logger

# from backend.storage.session_h5_manager import get_session_h5_path, get_storage_stats
# from backend.storage.task_repository import (
#     add_full_audio,
#     add_full_transcription,
#     add_webspeech_transcripts,
#     ensure_task_exists,
#     save_diarization_segments,
# )

logger = get_logger(__name__)


def worker_task(worker_id: int, session_id: str) -> dict:
    """Simulate worker writing to HDF5 (transcription + diarization + audio).

    Args:
        worker_id: Worker number (1-4)
        session_id: Session identifier

    Returns:
        Dict with worker results
    """
    start_time = time.time()
    logger.info(
        "WORKER_START",
        worker_id=worker_id,
        session_id=session_id,
    )

    try:
        # 1. Create task structures
        ensure_task_exists(session_id, TaskType.TRANSCRIPTION)
        ensure_task_exists(session_id, TaskType.DIARIZATION)

        # 2. Add webspeech transcripts (simulates frontend upload)
        transcripts = [f"Worker {worker_id} transcript line {i}" for i in range(5)]
        add_webspeech_transcripts(session_id, transcripts)

        # 3. Add full transcription (simulates STT result)
        full_text = f"Worker {worker_id} full transcription: Lorem ipsum dolor sit amet"
        add_full_transcription(session_id, full_text)

        # 4. Add audio file (simulates audio upload)
        audio_bytes = b"FAKE_AUDIO_DATA_" + str(worker_id).encode() * 1000
        add_full_audio(session_id, audio_bytes)

        # 5. Save diarization segments (simulates diarization worker)
        from backend.providers.diarization import DiarizationSegment, Speaker

        segments = [
            DiarizationSegment(
                speaker=Speaker(speaker_id="DOCTOR", name="Doctor"),
                text=f"Worker {worker_id} segment {i}",
                start_time=float(i),
                end_time=float(i + 1),
                confidence=0.95,
            )
            for i in range(3)
        ]
        save_diarization_segments(session_id, segments)

        elapsed = time.time() - start_time
        logger.info(
            "WORKER_SUCCESS",
            worker_id=worker_id,
            session_id=session_id,
            elapsed_seconds=round(elapsed, 3),
        )

        return {
            "worker_id": worker_id,
            "session_id": session_id,
            "success": True,
            "elapsed": round(elapsed, 3),
            "error": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            "WORKER_FAILED",
            worker_id=worker_id,
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "worker_id": worker_id,
            "session_id": session_id,
            "success": False,
            "elapsed": round(elapsed, 3),
            "error": str(e),
        }


def main():
    print("\n" + "=" * 70)
    print("🧪 CONCURRENT HDF5 WRITE TEST - Session-Level Architecture")
    print("=" * 70)
    print("Testing: 4 workers writing simultaneously to different session files")
    print("Expected: Zero concurrency conflicts, all workers succeed")
    print("=" * 70 + "\n")

    # Create 4 concurrent workers, each with its own session
    workers = 4
    sessions = [f"test-session-{i}" for i in range(1, workers + 1)]

    print("📋 Test Setup:")
    print(f"  Workers: {workers}")
    print(f"  Sessions: {', '.join(sessions)}")
    print()

    # Run workers concurrently
    print(f"🚀 Starting {workers} concurrent workers...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all workers
        futures = {
            executor.submit(worker_task, i + 1, session): (i + 1, session)
            for i, session in enumerate(sessions)
        }

        # Collect results
        results = []
        for future in as_completed(futures):
            worker_id, session = futures[future]
            result = future.result()
            results.append(result)
            status = "✅" if result["success"] else "❌"
            print(f"{status} Worker {worker_id} completed in {result['elapsed']}s")

    total_elapsed = time.time() - start_time

    # Analyze results
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)

    successes = sum(1 for r in results if r["success"])
    failures = sum(1 for r in results if not r["success"])

    print(f"Total elapsed:  {round(total_elapsed, 3)}s")
    print(f"Success rate:   {successes}/{workers} ({successes / workers * 100:.0f}%)")
    print(f"✅ Successes:   {successes}")
    print(f"❌ Failures:    {failures}")

    if failures > 0:
        print("\n❌ FAILED WORKERS:")
        for r in results:
            if not r["success"]:
                print(f"  Worker {r['worker_id']}: {r['error']}")

    # Show storage stats
    print("\n" + "=" * 70)
    print("💾 STORAGE STATS")
    print("=" * 70)
    stats = get_storage_stats()
    print(f"Session files created: {stats['session_files_count']}")
    print(f"Total size:            {stats['session_files_size_mb']:.2f} MB")

    # Verify session files exist
    print("\n" + "=" * 70)
    print("🔍 VERIFICATION")
    print("=" * 70)
    for session in sessions:
        path = get_session_h5_path(session)
        exists = "✅" if path.exists() else "❌"
        size = path.stat().st_size if path.exists() else 0
        print(f"{exists} {session}: {size:,} bytes")

    # Final verdict
    print("\n" + "=" * 70)
    if failures == 0:
        print("🎉 TEST PASSED: Zero concurrency conflicts!")
        print("   All 4 workers wrote to HDF5 simultaneously without errors.")
        print("   Session-level architecture is working correctly.")
    else:
        print("❌ TEST FAILED: Concurrency conflicts detected!")
        print(f"   {failures} worker(s) failed to write to HDF5.")
    print("=" * 70 + "\n")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
