#!/usr/bin/env python3
"""CLI interface for encryption worker.

Standalone command-line tool for encrypting HDF5 session data.

Usage:
    python -m backend.infrastructure.workers.tasks.encryption.cli <session_id> <h5_path> [--targets path1,path2,...]

Examples:
    $ python -m backend.infrastructure.workers.tasks.encryption.cli session_20251118_143022 /storage/corpus.h5
    $ python -m backend.infrastructure.workers.tasks.encryption.cli session_123 corpus.h5 --targets /audio/full_audio,/soap/note

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Hyperion Moon)
"""

from __future__ import annotations

import json
import sys

from backend.infrastructure.workers.tasks.encryption.worker import encrypt_session_worker


def main() -> int:
    """CLI entry point for encryption worker.

    Usage:
        python -m backend.infrastructure.workers.tasks.encryption.cli <session_id> <h5_path> [--targets path1,path2,...]

    Returns:
        Exit code (0 = success, 1 = failure)

    Examples:
        $ python -m backend.infrastructure.workers.tasks.encryption.cli session_20251118_143022 /storage/corpus.h5
        $ python -m backend.infrastructure.workers.tasks.encryption.cli session_123 corpus.h5 --targets /audio/full_audio,/soap/note
    """
    if len(sys.argv) < 3:
        print("Usage: python -m backend.infrastructure.workers.tasks.encryption.cli <session_id> <h5_path> [--targets path1,path2]")
        print()
        print("Examples:")
        print("  python -m backend.infrastructure.workers.tasks.encryption.cli session_20251118_143022 /storage/corpus.h5")
        print(
            "  python -m backend.infrastructure.workers.tasks.encryption.cli session_123 corpus.h5 --targets /audio/full_audio,/soap"
        )
        return 1

    session_id = sys.argv[1]
    h5_path = sys.argv[2]

    # Parse optional targets
    targets = None
    if len(sys.argv) > 3 and sys.argv[3] == "--targets":
        if len(sys.argv) < 5:
            print("Error: --targets requires comma-separated paths")
            return 1
        targets = sys.argv[4].split(",")

    # Run encryption
    result = encrypt_session_worker(session_id, h5_path, targets)

    # Output JSON result
    output = {
        "session_id": result.session_id,
        "status": result.status,
        "result": result.result,
        "duration_seconds": result.duration_seconds,
    }
    if result.error:
        output["error"] = result.error

    print(json.dumps(output, indent=2, ensure_ascii=False))

    return 0 if result.status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
