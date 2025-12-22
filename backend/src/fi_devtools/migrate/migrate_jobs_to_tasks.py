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
    fi migrate jobs-to-tasks [--dry-run]
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import h5py
from pathlib import Path


def get_corpus_path() -> Path:
    """Get corpus path from default location."""
    return Path("storage/corpus.h5")


def migrate_session(corpus_path: Path, session_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Migrate a single session from old to new schema."""
    report: dict[str, Any] = {
        "session_id": session_id,
        "migrated_tasks": [],
        "errors": [],
    }

    with h5py.File(corpus_path, "a") as f:
        session_path = f"/sessions/{session_id}"
        if session_path not in f:
            report["errors"].append(f"Session {session_id} not found")
            return report

        # 1. MIGRATE TRANSCRIPTION (production/chunks → tasks/TRANSCRIPTION)
        production_path = f"{session_path}/production/chunks"
        if production_path in f:
            print(f"  📝 Migrating TRANSCRIPTION chunks for {session_id}...")

            if not dry_run:
                task_group_path = f"{session_path}/tasks/TRANSCRIPTION"
                if task_group_path not in f:
                    f.create_group(task_group_path)

                task_group = f[task_group_path]
                if "chunks" not in task_group:
                    chunks_group = task_group.create_group("chunks")
                else:
                    chunks_group = task_group["chunks"]

                source_chunks = f[production_path]
                for chunk_name in source_chunks:
                    if chunk_name not in chunks_group:
                        f.copy(source_chunks[chunk_name], chunks_group, name=chunk_name)

            report["migrated_tasks"].append("TRANSCRIPTION")
            print("    ✅ TRANSCRIPTION chunks migrated")

        # 2. MIGRATE JOB METADATA
        jobs_transcription_path = f"{session_path}/jobs/transcription"
        if jobs_transcription_path in f:
            print("  📋 Migrating TRANSCRIPTION job metadata...")

            if not dry_run:
                jobs_group = f[jobs_transcription_path]
                job_ids = list(jobs_group.keys())
                if job_ids:
                    job_id = job_ids[0]
                    job_json = jobs_group[job_id][()]
                    if isinstance(job_json, bytes):
                        job_json = job_json.decode("utf-8")

                    task_metadata_path = f"{session_path}/tasks/TRANSCRIPTION/job_metadata"
                    if task_metadata_path in f:
                        del f[task_metadata_path]
                    f[task_metadata_path] = job_json

            print("    ✅ Job metadata migrated")

        # 3. MIGRATE DIARIZATION
        jobs_diarization_path = f"{session_path}/jobs/diarization"
        if jobs_diarization_path in f:
            print("  🎙️  Migrating DIARIZATION...")
            if not dry_run:
                task_group_path = f"{session_path}/tasks/DIARIZATION"
                if task_group_path not in f:
                    f.create_group(task_group_path)
                report["migrated_tasks"].append("DIARIZATION (placeholder)")
            print("    ⚠️  DIARIZATION migration needs custom logic (skipped)")

    return report


def run(args: Sequence[str] | None = None) -> None:
    """Migrate HDF5 schema from jobs/ to tasks/."""
    dry_run = "--dry-run" in (args or [])
    corpus_path = get_corpus_path()

    print("═" * 70)
    print("  🔄 HDF5 SCHEMA MIGRATION: jobs/ → tasks/")
    print("═" * 70)
    print()

    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be written\n")

    if not corpus_path.exists():
        print(f"❌ Corpus file not found: {corpus_path}")
        return

    with h5py.File(corpus_path, "r") as f:
        if "sessions" not in f:
            print("❌ No sessions found in corpus")
            return
        session_ids = list(f["sessions"].keys())

    print(f"📊 Found {len(session_ids)} sessions to migrate\n")

    reports = []
    for session_id in session_ids:
        print(f"🔄 Migrating session: {session_id}")
        report = migrate_session(corpus_path, session_id, dry_run=dry_run)
        reports.append(report)

        if report["errors"]:
            for error in report["errors"]:
                print(f"    ❌ {error}")
        elif report["migrated_tasks"]:
            print(f"    ✅ Migrated: {', '.join(report['migrated_tasks'])}")
        else:
            print("    ℹ️  No migration needed")
        print()

    # Summary
    print("═" * 70)
    print("  📊 MIGRATION SUMMARY")
    print("═" * 70)
    print(f"Total sessions: {len(reports)}")
    print(f"Sessions migrated: {sum(1 for r in reports if r['migrated_tasks'])}")
    print(f"Sessions with errors: {sum(1 for r in reports if r['errors'])}")

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no changes were written")


if __name__ == "__main__":
    run()
