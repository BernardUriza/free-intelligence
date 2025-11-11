#!/usr/bin/env python3
"""Check HDF5 corpus chunks - Sanity test for end-to-end pipeline.

Card: AUR-PROMPT-4.2 Fix Pack
Usage: python scripts/check-h5-chunks.py
"""

from __future__ import annotations

import os
from pathlib import Path

import h5py


def main():
    corpus_path = Path(os.getenv("AURITY_CORPUS_H5", "storage/corpus.h5"))

    if not corpus_path.exists():
        print(f"❌ Corpus not found: {corpus_path}")
        return

    print(f"✅ Corpus exists: {corpus_path} ({corpus_path.stat().st_size} bytes)\n")

    with h5py.File(corpus_path, "r") as f:
        if "sessions" not in f:
            print("❌ No sessions group in corpus")
            return

        sessions = list(f["sessions"].keys())
        print(f"📂 Sessions: {len(sessions)}\n")

        for session_id in sorted(sessions)[-5:]:  # Last 5 sessions
            session_grp = f[f"sessions/{session_id}"]

            if "chunks" not in session_grp:
                print(f"   ⚠️  {session_id}: No chunks")
                continue

            ds = session_grp["chunks"]
            print(f"   ✅ {session_id}:")
            print(f"      Chunks: {ds.shape[0]}")
            print(f"      Dtype: {ds.dtype}")

            # Show first 3 chunks
            for i in range(min(3, ds.shape[0])):
                row = ds[i]
                chunk_id = row["chunk_id"].decode("utf-8")
                chunk_num = row["chunk_number"]
                transcript = row["transcription"]
                duration = row["duration"]
                created = row["created_at"]

                print(
                    f"      [{i}] chunk_{chunk_num}: \"{transcript[:40]}...\" "
                    f"({duration:.1f}s) @ {created}"
                )

            print()


if __name__ == "__main__":
    main()
