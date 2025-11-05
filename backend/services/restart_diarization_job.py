#!/usr/bin/env python3
"""
Script to manually restart a cancelled diarization job.

Usage:
    python3 scripts/restart_diarization_job.py <job_id> [from_chunk]

Example:
    python3 scripts/restart_diarization_job.py f2667c96-105b-42c7-b385-2e20417a7fff 24
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import h5py


def restart_diarization_job(job_id: str, from_chunk: int = 0):
    """Restart a diarization job from a specific chunk."""
    h5_path = Path("storage/diarization.h5")

    if not h5_path.exists():
        print(f"✗ HDF5 file not found: {h5_path}")
        return False

    try:
        with h5py.File(h5_path, "r+") as h5:
            # Check if job exists in diarization/ group
            if f"diarization/{job_id}" not in h5:
                print(f"✗ Job not found: {job_id}")
                print("Available jobs:")
                if "diarization" in h5:
                    for j in h5["diarization"].keys():
                        print(f"  - {j}")
                return False

            job_group = h5[f"diarization/{job_id}"]

            # Get current metadata
            status = (
                job_group.attrs.get("status", "").decode()
                if isinstance(job_group.attrs.get("status"), bytes)
                else job_group.attrs.get("status")
            )
            session_id = (
                job_group.attrs.get("session_id", "").decode()
                if isinstance(job_group.attrs.get("session_id"), bytes)
                else job_group.attrs.get("session_id")
            )
            total_chunks = job_group.attrs.get("total_chunks", 0)
            processed_chunks = job_group.attrs.get("processed_chunks", 0)

            print(f"Job ID: {job_id}")
            print(f"Session ID: {session_id}")
            print(f"Current Status: {status}")
            print(f"Processed Chunks: {processed_chunks}/{total_chunks}")
            print(f"Restarting from chunk: {from_chunk}")
            print("")

            # Update status to "processing"
            job_group.attrs["status"] = "processing"
            job_group.attrs["updated_at"] = datetime.now(UTC).isoformat()

            print("✓ Job status updated to 'processing'")
            print(f"✓ Updated at: {job_group.attrs['updated_at']}")
            print("")
            print("The worker should resume processing from chunk", from_chunk)
            print(
                "Monitor progress with: curl http://localhost:7001/api/diarization/jobs/" + job_id
            )

            return True

    except Exception as e:
        print(f"✗ Error restarting job: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/restart_diarization_job.py <job_id> [from_chunk]")
        sys.exit(1)

    job_id = sys.argv[1]
    from_chunk = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    success = restart_diarization_job(job_id, from_chunk)
    sys.exit(0 if success else 1)
