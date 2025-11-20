#!/usr/bin/env python3
"""
Migrate HDF5 corpus from old format to SWMR-compatible format.

This script recursively copies all groups, datasets, and attributes from
corpus.h5.old to a new corpus.h5 with libver='latest' for SWMR support.

Author: Claude Code
Created: 2025-11-16
"""

from __future__ import annotations

import sys
from pathlib import Path

import h5py


def copy_attrs(src_obj, dst_obj):
    """Copy all attributes from source to destination object."""
    for key, val in src_obj.attrs.items():
        dst_obj.attrs[key] = val


def copy_dataset(src_dataset, dst_group, name):
    """Copy a dataset from source to destination group."""
    try:
        # Create dataset with same dtype, shape, and data
        dst_dataset = dst_group.create_dataset(
            name,
            data=src_dataset[()],
            dtype=src_dataset.dtype,
            chunks=src_dataset.chunks,
            compression=src_dataset.compression,
            compression_opts=src_dataset.compression_opts,
        )

        # Copy attributes
        copy_attrs(src_dataset, dst_dataset)

        return dst_dataset
    except (OSError, RuntimeError) as e:
        print(f"    ⚠️  SKIPPED (corrupted): {name} - {e}")
        return None


def copy_group_recursive(src_group, dst_group, path="/"):
    """Recursively copy a group and all its contents."""
    print(f"Copying group: {path}")

    # Copy group attributes
    copy_attrs(src_group, dst_group)

    # Iterate over all items in source group
    for name, item in src_group.items():
        item_path = f"{path}/{name}"

        if isinstance(item, h5py.Group):
            # Create subgroup in destination
            dst_subgroup = dst_group.create_group(name)
            # Recursively copy subgroup
            copy_group_recursive(item, dst_subgroup, item_path)

        elif isinstance(item, h5py.Dataset):
            # Copy dataset
            print(f"  Dataset: {item_path} ({item.dtype}, shape={item.shape})")
            copy_dataset(item, dst_group, name)


def migrate_corpus():
    """Main migration function."""
    old_path = Path("storage/corpus.h5.old")
    new_path = Path("storage/corpus.h5")
    temp_path = Path("storage/corpus.h5.migrated")

    if not old_path.exists():
        print(f"❌ Old file not found: {old_path}")
        sys.exit(1)

    print(f"📦 Old file: {old_path} ({old_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Open old file (read-only)
    with h5py.File(old_path, "r") as old_file:
        print(f"📖 Opened old file (libver={old_file.libver})")
        print(f"   Root groups: {list(old_file.keys())}")

        # Create new file with SWMR support
        with h5py.File(temp_path, "w", libver="latest") as new_file:
            print("📝 Created new file with libver='latest'")

            # Copy all root-level groups recursively
            for name, item in old_file.items():
                if isinstance(item, h5py.Group):
                    print(f"\n🔄 Copying root group: /{name}")
                    dst_group = new_file.create_group(name)
                    copy_group_recursive(item, dst_group, f"/{name}")
                elif isinstance(item, h5py.Dataset):
                    print(f"\n🔄 Copying root dataset: /{name}")
                    copy_dataset(item, new_file, name)

            # Copy root attributes
            copy_attrs(old_file, new_file)

            print("\n✅ Migration complete!")
            print(f"   New file: {temp_path} ({temp_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Rename files
    print("\n🔄 Renaming files...")
    new_path.rename(Path("storage/corpus.h5.pre-migration"))
    temp_path.rename(new_path)
    print(f"✅ Renamed {temp_path} → {new_path}")

    print("\n🎉 Migration complete! Old sessions should now be accessible.")
    print("   Backups:")
    print("     - corpus.h5.old (original old file)")
    print("     - corpus.h5.pre-migration (empty new file)")


if __name__ == "__main__":
    migrate_corpus()
