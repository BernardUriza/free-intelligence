#!/usr/bin/env python3.14
"""Refactor worker files to use DI container instead of broken imports.

This script updates worker files that import task_repository functions
to use the DI container pattern instead.
"""

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent

# Worker files to refactor
WORKER_FILES = [
    "core/infrastructure/workers/tasks/transcription_worker.py",
    "core/infrastructure/workers/tasks/diarization_worker.py",
    "core/infrastructure/workers/tasks/soap_worker.py",
    "core/infrastructure/workers/tasks/emotion_worker.py",
]

# Replacement pattern for imports
IMPORT_REPLACEMENT = """from backend.container import get_container  # type: ignore[assignment]

    # Use DI container for task repository functions
    def get_task_metadata(session_id: str, task_type: Any) -> dict | None:
        \"\"\"Get task metadata via DI container.\"\"\"
        task_repo = get_container().get_task_repository()
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        return task_repo.get_container().get_task_repository().get_task_metadata(session_id, task_type_str)

    def update_task_metadata(session_id: str, task_type: Any, metadata: dict) -> None:
        \"\"\"Update task metadata via DI container.\"\"\"
        task_repo = get_container().get_task_repository()
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        task_repo.get_container().get_task_repository().save_task_metadata(session_id, task_type_str, metadata)

    def ensure_get_container().get_task_repository().task_exists(session_id: str, task_type: Any, metadata: dict | None = None) -> str:
        \"\"\"Ensure task exists via DI container.\"\"\"
        task_repo = get_container().get_task_repository()
        task_type_str = task_type.value if hasattr(task_type, 'value') else str(task_type)
        return task_repo.ensure_get_container().get_task_repository().task_exists(session_id, task_type_str, metadata)

    HAS_BACKEND_IMPORTS = True"""


def refactor_worker(file_path: Path) -> bool:
    """Refactor a single worker file.

    Returns:
        True if file was modified
    """
    if not file_path.exists():
        print(f"⏭️  SKIP: {file_path} (not found)")
        return False

    content = file_path.read_text()

    # Check if already refactored
    if "get_container().get_task_repository()" in content:
        print(f"⏭️  SKIP: {file_path.name} (already refactored)")
        return False

    # Find the try block with backend imports

    match = re.search(pattern, content)
    if not match:
        print(f"⚠️  WARNING: {file_path.name} (pattern not found - may need manual fix)")
        return False

    # Replace with DI container version
    before_imports = match.group(1)
    new_content = re.sub(
        pattern,
        before_imports + IMPORT_REPLACEMENT,
        content,
        count=1
    )

    if new_content != content:
        file_path.write_text(new_content)
        print(f"✅ FIXED: {file_path.name}")
        return True

    return False


def main():
    """Main execution."""
    print("🔄 Refactoring worker files to use DI container...\n")

    modified_count = 0
    for worker_file in WORKER_FILES:
        file_path = BACKEND_DIR / worker_file
        if refactor_worker(file_path):
            modified_count += 1

    print(f"\n🎉 Complete: {modified_count}/{len(WORKER_FILES)} workers refactored")


if __name__ == "__main__":
    main()
