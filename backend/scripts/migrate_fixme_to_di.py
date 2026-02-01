#!/usr/bin/env python3.14
"""Migrate FIXME commented imports to DI container usage.

This script:
1. Finds all files with FIXME comments
2. Adds DI container import
3. Replaces direct function calls with DI container calls
4. Removes FIXME comments

Author: Claude Code (mentor mode)
Date: 2026-01-27
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple

# Function mapping: old function name → repository method
FUNCTION_TO_REPO_METHOD = {
    # Task repository - Core methods
    "get_task_metadata": "get_task_repository().get_task_metadata",
    "task_exists": "get_task_repository().task_exists",
    "ensure_task_exists": "get_task_repository().ensure_task_exists",
    "save_task_metadata": "get_task_repository().save_task_metadata",
    "get_task_chunks": "get_task_repository().get_task_chunks",

    # Task repository - Chunk operations
    "batch_update_chunk_datasets": "get_task_repository().batch_update_chunk_datasets",
    "get_chunk_audio_bytes": "get_task_repository().get_chunk_audio_bytes",

    # Task repository - Diarization
    "save_diarization_segments": "get_task_repository().save_diarization_segments",
    "get_diarization_segments": "get_task_repository().get_diarization_segments",

    # Task repository - SOAP
    "save_soap_data": "get_task_repository().save_soap_data",
    "get_soap_data": "get_task_repository().get_soap_data",

    # Task repository - Orders
    "create_order": "get_task_repository().create_order",
    "get_orders": "get_task_repository().get_orders",
    "update_order": "get_task_repository().update_order",
    "delete_order": "get_task_repository().delete_order",

    # Task repository - Session finalization
    "add_full_audio": "get_task_repository().add_full_audio",
    "add_full_transcription": "get_task_repository().add_full_transcription",
    "add_webspeech_transcripts": "get_task_repository().add_webspeech_transcripts",

    # Session service (via DI)
    "get_session": "get_session_service().get_session",
    "create_session": "get_session_service().create_session",
    "update_session": "get_session_service().update_session",
    "list_sessions": "get_session_service().list_sessions",
}


def find_files_with_fixme() -> List[Path]:
    """Find all Python files with FIXME comments."""
    try:
        result = subprocess.run(
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            files = [Path(f) for f in result.stdout.strip().split('\n') if f]
            return files
        return []
    except Exception as e:
        print(f"❌ Error finding FIXME files: {e}")
        return []


def has_di_import(content: str) -> bool:
    """Check if file already imports get_container."""
    return "from backend.container import get_container" in content


def add_di_import(content: str) -> str:
    """Add DI container import if not present."""
    if has_di_import(content):
        return content

    lines = content.split('\n')

    # Find first import block after docstring/comments
    insert_at = 0
    in_docstring = False

    for i, line in enumerate(lines):
        # Track docstrings
        if '"""' in line or "'''" in line:
            in_docstring = not in_docstring

        # Skip docstrings and comments
        if in_docstring or line.strip().startswith('#'):
            continue

        # Find first real import
        if line.startswith('from ') or line.startswith('import '):
            insert_at = i
            break

    # Insert DI import
    lines.insert(insert_at, 'from backend.container import get_container')

    return '\n'.join(lines)


def replace_function_calls(content: str) -> Tuple[str, int]:
    """Replace direct function calls with DI container calls.

    Returns:
        Tuple of (modified_content, number_of_replacements)
    """
    replacements = 0

    for old_func, repo_method in FUNCTION_TO_REPO_METHOD.items():
        # Pattern: function_name( but not def function_name or # function_name
        pattern = rf'(?<!def\s)(?<!#\s){old_func}\('

        # Count matches first
        matches = re.findall(pattern, content)
        if matches:
            replacement = f'get_container().{repo_method}('
            content = re.sub(pattern, replacement, content)
            replacements += len(matches)
            print(f"  Replaced {len(matches)} calls to {old_func}()")

    return content, replacements


def remove_fixme_comments(content: str) -> Tuple[str, int]:
    """Remove FIXME comment blocks.

    Returns:
        Tuple of (modified_content, number_of_fixme_blocks_removed)
    """
    lines = content.split('\n')
    new_lines = []
    fixme_count = 0
    skip_until_non_comment = False

    for line in lines:
        # Check if this is a FIXME line
            fixme_count += 1
            skip_until_non_comment = True
            continue

        # Skip commented imports after FIXME
        if skip_until_non_comment:
            if line.strip().startswith('#'):
                continue
            else:
                skip_until_non_comment = False

        new_lines.append(line)

    return '\n'.join(new_lines), fixme_count


def migrate_file(file_path: Path) -> bool:
    """Migrate a single file from FIXME imports to DI.

    Returns:
        True if file was modified
    """
    print(f"\n📄 Processing {file_path}...")

    try:
        content = file_path.read_text()
        original_content = content

        # Step 1: Add DI import
        if not has_di_import(content):
            content = add_di_import(content)
            print("  ✅ Added DI import")
        else:
            print("  ⏭️  Already has DI import")

        # Step 2: Replace function calls
        content, replacements = replace_function_calls(content)
        if replacements > 0:
            print(f"  ✅ Replaced {replacements} function calls")

        # Step 3: Remove FIXME comments
        content, fixme_count = remove_fixme_comments(content)
        if fixme_count > 0:
            print(f"  ✅ Removed {fixme_count} FIXME blocks")

        # Save if modified
        if content != original_content:
            file_path.write_text(content)
            print(f"  💾 Saved changes")
            return True
        else:
            print(f"  ⏭️  No changes needed")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main migration script."""
    print("🔍 Finding files with FIXME comments...")

    files = find_files_with_fixme()

    if not files:
        print("✅ No files with FIXME comments found!")
        return

    print(f"Found {len(files)} files with FIXME imports\n")
    print("=" * 60)

    modified_count = 0
    skipped_count = 0

    for file in files:
        if migrate_file(file):
            modified_count += 1
        else:
            skipped_count += 1

    print("\n" + "=" * 60)
    print(f"\n✅ Migration complete!")
    print(f"  Modified: {modified_count} files")
    print(f"  Skipped: {skipped_count} files")
    print(f"  Total: {len(files)} files")

    if modified_count > 0:
        print("\n⚠️  Next steps:")
        print("  1. Run syntax check: python3.14 -m py_compile <modified_files>")
        print("  2. Run tests: pytest backend/tests/")
        print("  3. Review changes: git diff")


if __name__ == "__main__":
    main()
