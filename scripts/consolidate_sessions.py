#!/usr/bin/env python3
"""Consolidate session HDF5 files into main corpus.h5.

Usage:
    # Consolidate all sessions
    python scripts/consolidate_sessions.py --all

    # Consolidate specific session
    python scripts/consolidate_sessions.py --session abc-123-def

    # Consolidate with dry-run (no actual changes)
    python scripts/consolidate_sessions.py --all --dry-run

    # Consolidate but keep session files (don't delete after)
    python scripts/consolidate_sessions.py --all --keep-files

Created: 2025-12-03
Purpose: Merge session-level HDF5 files into main corpus for long-term storage
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.logger import get_logger
from backend.storage.session_h5_manager import (
    SESSIONS_DIR,
    consolidate_all_sessions,
    consolidate_session_to_corpus,
    get_storage_stats,
    list_all_sessions,
)

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate session HDF5 files into corpus.h5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--session",
        type=str,
        help="Consolidate specific session ID",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Consolidate all session files",
    )

    parser.add_argument(
        "--max",
        type=int,
        help="Maximum number of sessions to consolidate (with --all)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be consolidated without actually doing it",
    )

    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep session files after consolidation (don't delete)",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show storage statistics and exit",
    )

    args = parser.parse_args()

    # Show stats
    if args.stats:
        stats = get_storage_stats()
        print("\n" + "=" * 70)
        print("📊 STORAGE STATISTICS")
        print("=" * 70)
        print(f"Session files:     {stats['session_files_count']}")
        print(f"Session files size: {stats['session_files_size_mb']:.2f} MB")
        print(f"Corpus size:        {stats['corpus_size_mb']:.2f} MB")
        print(f"Total sessions:     {stats['total_sessions']}")
        print("=" * 70 + "\n")
        return 0

    # Consolidate specific session
    if args.session:
        print(f"\n🔄 Consolidating session: {args.session}")

        if args.dry_run:
            print(f"[DRY RUN] Would consolidate session {args.session}")
            return 0

        try:
            success = consolidate_session_to_corpus(
                args.session,
                delete_after=not args.keep_files,
            )
            if success:
                print(f"✅ Successfully consolidated session: {args.session}")
                return 0
            else:
                print(f"❌ Failed to consolidate session: {args.session}")
                return 1
        except Exception as e:
            print(f"❌ Error consolidating session {args.session}: {e}")
            return 1

    # Consolidate all sessions
    if args.all:
        # Get list of sessions
        if not SESSIONS_DIR.exists():
            print(f"❌ Sessions directory not found: {SESSIONS_DIR}")
            return 1

        session_files = list(SESSIONS_DIR.glob("*.h5"))
        if not session_files:
            print("ℹ️  No session files to consolidate")
            return 0

        count = len(session_files)
        if args.max:
            count = min(count, args.max)

        print(f"\n🔄 Consolidating {count} session file(s)...")

        if args.dry_run:
            print(f"[DRY RUN] Would consolidate {count} sessions:")
            for path in session_files[:count]:
                print(f"  - {path.stem}")
            return 0

        # Consolidate
        stats = consolidate_all_sessions(max_sessions=args.max)

        print("\n" + "=" * 70)
        print("📊 CONSOLIDATION RESULTS")
        print("=" * 70)
        print(f"✅ Success:  {stats['success']}")
        print(f"❌ Failed:   {stats['failed']}")
        print(f"⏭️  Skipped:  {stats['skipped']}")
        print("=" * 70 + "\n")

        return 0 if stats["failed"] == 0 else 1

    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
