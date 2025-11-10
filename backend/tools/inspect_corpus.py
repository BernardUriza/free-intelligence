#!/usr/bin/env python3
"""
Inspect Corpus HDF5 - Free Intelligence

Muestra la estructura completa del corpus de forma legible.

Usage:
    python3 scripts/inspect_corpus.py
"""

import sys
from pathlib import Path

import h5py


def inspect_corpus(corpus_path="storage/corpus.h5"):
    """Inspecciona y muestra estructura del corpus."""

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

        def print_structure(name, obj, indent=0):
            """Recursively print HDF5 structure."""
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
                    print(f"   [{i+1}]")
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
                        f"   Latest operation: {f['/audit_logs/operation'][audit_count-1].decode('utf-8')}"
                    )
            else:
                print("   Audit Logs: Group exists but empty")
            print()

    print("=" * 60)
    print("✅ Inspection complete!")
    print()
    print("Tip: Use h5web extension in VS Code for interactive viewing")
    print("     Extension ID: h5web.vscode-h5web")


if __name__ == "__main__":
    corpus_path = sys.argv[1] if len(sys.argv) > 1 else "storage/corpus.h5"

    if not Path(corpus_path).exists():
        print(f"❌ Error: File not found: {corpus_path}")
        sys.exit(1)

    inspect_corpus(corpus_path)
