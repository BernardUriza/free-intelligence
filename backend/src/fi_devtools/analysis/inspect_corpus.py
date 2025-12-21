#!/usr/bin/env python3
"""Inspect Corpus HDF5 - Free Intelligence.

Shows the complete corpus structure in a human-readable format.

Usage:
    fi analysis inspect-corpus
    fi analysis inspect-corpus storage/corpus.h5
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def print_structure(name: str, obj: Any, indent: int = 0) -> None:
    """Recursively print HDF5 structure."""
    import h5py

    prefix = "   " * indent

    if isinstance(obj, h5py.Group):
        print(f"{prefix}📁 {name}/ (Group)")
        # Print attributes
        if obj.attrs:
            for key, value in obj.attrs.items():
                print(f"{prefix}   🏷️  {key}: {value}")
    elif isinstance(obj, h5py.Dataset):
        print(f"{prefix}📊 {name} (Dataset)")
        print(f"{prefix}   Shape: {obj.shape}")
        print(f"{prefix}   Dtype: {obj.dtype}")
        print(f"{prefix}   Size: {obj.size} elements")
        if obj.compression:
            print(f"{prefix}   Compression: {obj.compression}")


def inspect_corpus(corpus_path: str = "storage/corpus.h5") -> None:
    """Inspect and show corpus structure."""
    import h5py

    print("🔍 FREE INTELLIGENCE - CORPUS INSPECTOR")
    print("=" * 60)
    print(f"\n📁 File: {corpus_path}\n")

    with h5py.File(corpus_path, "r") as f:
        # File info
        file_size_mb = Path(corpus_path).stat().st_size / (1024 * 1024)
        print(f"📊 File Size: {file_size_mb:.2f} MB")
        print(f"📦 Groups: {len(list(f.keys()))}")
        print()

        # Metadata
        print("🏷️  METADATA")
        print("-" * 60)
        if "/metadata/" in f:
            for key, value in f["/metadata/"].attrs.items():
                print(f"   {key}: {value}")
        print()

        # Groups structure
        print("📂 GROUPS STRUCTURE")
        print("-" * 60)

        f.visititems(print_structure)
        print()

        # Data samples
        print("📖 DATA SAMPLES")
        print("-" * 60)

        # Interactions
        if "/interactions/" in f:
            interactions_count = f["/interactions/prompt"].shape[0]
            print(f"\n   Interactions: {interactions_count} total")

            if interactions_count > 0:
                # Show last 3
                show_count = min(3, interactions_count)
                print(f"   Showing last {show_count}:\n")

                for i in range(interactions_count - show_count, interactions_count):
                    print(f"   [{i + 1}]")
                    print(f"      Session: {f['/interactions/session_id'][i].decode('utf-8')}")
                    print(f"      Timestamp: {f['/interactions/timestamp'][i].decode('utf-8')}")

                    prompt = f["/interactions/prompt"][i].decode("utf-8")
                    print(f"      Prompt: {prompt[:60]}...")

                    response = f["/interactions/response"][i].decode("utf-8")
                    print(f"      Response: {response[:60]}...")

                    print(f"      Model: {f['/interactions/model'][i].decode('utf-8')}")
                    print(f"      Tokens: {f['/interactions/tokens'][i]}")
                    print()

        # Embeddings
        if "/embeddings/" in f:
            embeddings_count = f["/embeddings/vector"].shape[0]
            print(f"   Embeddings: {embeddings_count} total")
            print(f"   Vector dimensions: {f['/embeddings/vector'].shape[1]}")
            print(
                f"   Model: {f['/embeddings/model'][0].decode('utf-8') if embeddings_count > 0 else 'N/A'}"
            )
            print()

        # Audit logs
        if "/audit_logs/" in f:
            if "audit_id" in f["/audit_logs/"]:  # type: ignore[operator]
                audit_count = f["/audit_logs/audit_id"].shape[0]
                print(f"   Audit Logs: {audit_count} total")

                if audit_count > 0:
                    print(
                        f"   Latest operation: {f['/audit_logs/operation'][audit_count - 1].decode('utf-8')}"
                    )
            else:
                print("   Audit Logs: Group exists but empty")
            print()

    print("=" * 60)
    print("✅ Inspection complete!")
    print()
    print("Tip: Use h5web extension in VS Code for interactive viewing")
    print("     Extension ID: h5web.vscode-h5web")


def run(args: Sequence[str] | None = None) -> None:
    """Inspect corpus HDF5 file."""
    corpus_path = next(iter(args or [])) if args else "storage/corpus.h5"

    if not Path(corpus_path).exists():
        print(f"❌ Error: File not found: {corpus_path}")
        sys.exit(1)

    inspect_corpus(corpus_path)


if __name__ == "__main__":
    run(sys.argv[1:] if len(sys.argv) > 1 else None)
