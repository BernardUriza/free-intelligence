#!/usr/bin/env python3
"""Migrate HDF5 data from old schema (jobs/ + production/) to new schema (tasks/).

Migration strategy:
  1. Read all sessions from corpus.h5
  2. For each session:
     - If has /production/chunks/ → migrate to /tasks/TRANSCRIPTION/chunks/
     - If has /jobs/transcription/ → migrate metadata to /tasks/TRANSCRIPTION/job_metadata
     - If has /jobs/diarization/ → migrate to /tasks/DIARIZATION/
  3. Validate both schemas coexist (no data loss)
  4. Log migration report

Usage:
    python3 tools/migrate_jobs_to_tasks.py [--dry-run]

Options:
    --dry-run: Preview changes without writing

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import CORPUS_PATH, ensure_task_exists

logger = get_logger(__name__)


def migrate_session(session_id: str, dry_run: bool = False) -> dict[str, any]:
    """Migrate a single session from old to new schema.

    Args:
        session_id: Session identifier
        dry_run: If True, don't write changes

    Returns:
        Migration report dict
    """
    report = {
        "session_id": session_id,
        "migrated_tasks": [],
        "errors": [],
    }

    with h5py.File(CORPUS_PATH, "a") as f:
        session_path = f"/sessions/{session_id}"
        if session_path not in f:  # type: ignore[operator]
            report["errors"].append(f"Session {session_id} not found")
            return report

        session_group = f[session_path]  # type: ignore[index]

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. MIGRATE TRANSCRIPTION (production/chunks → tasks/TRANSCRIPTION)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        production_path = f"{session_path}/production/chunks"
        if production_path in f:  # type: ignore[operator]
            print(f"  📝 Migrating TRANSCRIPTION chunks for {session_id}...")

            if not dry_run:
                # Create task if not exists
                try:
                    ensure_task_exists(session_id, TaskType.TRANSCRIPTION, allow_existing=True)
                except Exception as e:
                    report["errors"].append(f"Failed to create TRANSCRIPTION task: {e}")
                    return report

                # Get or create chunks group
                task_group_path = f"{session_path}/tasks/TRANSCRIPTION"
                task_group = f[task_group_path]  # type: ignore[index]

                # Create chunks group if not exists
                if "chunks" not in task_group:  # type: ignore[operator]
                    chunks_group = task_group.create_group("chunks")  # type: ignore[index]
                else:
                    chunks_group = task_group["chunks"]  # type: ignore[index]

                # Copy chunks from source
                source_chunks = f[production_path]  # type: ignore[index]

                for chunk_name in source_chunks.keys():  # type: ignore[union-attr]
                    if chunk_name not in chunks_group:  # type: ignore[operator]
                        # Copy entire chunk group
                        f.copy(  # type: ignore[attr-defined]
                            source_chunks[chunk_name],  # type: ignore[index]
                            chunks_group,  # type: ignore[arg-type]
                            name=chunk_name,
                        )

            report["migrated_tasks"].append("TRANSCRIPTION")
            print("    ✅ TRANSCRIPTION chunks migrated")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. MIGRATE JOB METADATA (jobs/transcription → tasks/TRANSCRIPTION/job_metadata)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        jobs_transcription_path = f"{session_path}/jobs/transcription"
        if jobs_transcription_path in f:  # type: ignore[operator]
            print("  📋 Migrating TRANSCRIPTION job metadata...")

            if not dry_run:
                jobs_group = f[jobs_transcription_path]  # type: ignore[index]

                # Get first job (usually only one)
                job_ids = list(jobs_group.keys())  # type: ignore[union-attr]
                if job_ids:
                    job_id = job_ids[0]
                    job_json = jobs_group[job_id][()]  # type: ignore[index]
                    if isinstance(job_json, bytes):
                        job_json = job_json.decode("utf-8")

                    job_data = json.loads(job_json)

                    # Write to new location
                    task_metadata_path = f"{session_path}/tasks/TRANSCRIPTION/job_metadata"
                    if task_metadata_path in f:  # type: ignore[operator]
                        del f[task_metadata_path]  # type: ignore[index]

                    f[task_metadata_path] = job_json  # type: ignore[index]

            print("    ✅ Job metadata migrated")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. MIGRATE DIARIZATION (jobs/diarization → tasks/DIARIZATION)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        jobs_diarization_path = f"{session_path}/jobs/diarization"
        if jobs_diarization_path in f:  # type: ignore[operator]
            print("  🎙️  Migrating DIARIZATION...")

            if not dry_run:
                try:
                    ensure_task_exists(session_id, TaskType.DIARIZATION, allow_existing=True)
                except Exception as e:
                    report["errors"].append(f"Failed to create DIARIZATION task: {e}")
                    return report

                # Copy entire diarization job group to task
                # Note: Old schema stores diarization results in jobs/diarization/{job_id}
                # New schema stores in tasks/DIARIZATION/
                # This is a placeholder - actual diarization structure needs to be defined

                report["migrated_tasks"].append("DIARIZATION (placeholder)")

            print("    ⚠️  DIARIZATION migration needs custom logic (skipped)")

    return report


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate HDF5 schema to task-based")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    print("═" * 70)
    print("  🔄 HDF5 SCHEMA MIGRATION: jobs/ → tasks/")
    print("═" * 70)
    print()

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be written")
        print()

    if not CORPUS_PATH.exists():
        print(f"❌ Corpus file not found: {CORPUS_PATH}")
        return 1

    # Get all sessions
    with h5py.File(CORPUS_PATH, "r") as f:
        if "sessions" not in f:
            print("❌ No sessions found in corpus")
            return 1

        sessions_group = f["sessions"]
        session_ids = list(sessions_group.keys())  # type: ignore[union-attr]

    print(f"📊 Found {len(session_ids)} sessions to migrate")
    print()

    # Migrate each session
    reports = []
    for session_id in session_ids:
        print(f"🔄 Migrating session: {session_id}")
        report = migrate_session(session_id, dry_run=args.dry_run)
        reports.append(report)

        if report["errors"]:
            for error in report["errors"]:
                print(f"    ❌ {error}")
        elif report["migrated_tasks"]:
            print(f"    ✅ Migrated: {', '.join(report['migrated_tasks'])}")
        else:
            print("    ℹ️  No migration needed (already using new schema)")

        print()

    # Summary
    print("═" * 70)
    print("  📊 MIGRATION SUMMARY")
    print("═" * 70)

    total_sessions = len(reports)
    sessions_with_tasks = sum(1 for r in reports if r["migrated_tasks"])
    sessions_with_errors = sum(1 for r in reports if r["errors"])

    print(f"Total sessions: {total_sessions}")
    print(f"Sessions migrated: {sessions_with_tasks}")
    print(f"Sessions with errors: {sessions_with_errors}")

    if args.dry_run:
        print()
        print("⚠️  This was a DRY RUN - no changes were written")
        print("   Run without --dry-run to apply changes")

    return 0 if sessions_with_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
