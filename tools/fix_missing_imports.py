#!/usr/bin/env python3
"""Fix missing imports by updating to correct module paths."""

import re
from pathlib import Path

# Mapping of old imports to new imports
IMPORT_FIXES = {
    "backend.llm_adapter": "backend.providers.llm_adapter",
    "backend.timeline_models": "backend.schemas.timeline_models",
    "backend.policy_enforcer": "backend.policy.policy_enforcer",
    "backend.corpus_ops": "backend.storage.corpus_ops",
    "backend.services.transcription_service": "backend.services.transcription.service",
    "backend.export_policy": "backend.policy.export_policy",
    "backend.diarization_service": "backend.services.diarization_service",
    "backend.append_only_policy": "backend.policy.append_only_policy",
    "backend.llm_router": "backend.providers.llm_router",
    "backend.corpus_identity": "backend.storage.corpus_identity",
    "backend.api.timeline_verify": "backend.api.internal.timeline_verify",
    "backend.common.audit_logs": "backend.services.audit_service",
    "backend.services.audit_logs": "backend.services.audit_service",
    "backend.adapters_redux": "backend.providers.adapters_redux",
    "backend.fi_consult_models": "backend.providers.fi_consult_models",
}


def fix_imports_in_file(filepath: Path) -> int:
    """Fix imports in a single file."""
    try:
        content = filepath.read_text()
        original = content

        for old_import, new_import in IMPORT_FIXES.items():
            # Fix "from X import ..."
            content = re.sub(rf"\bfrom {re.escape(old_import)}\b", f"from {new_import}", content)
            # Fix "import X"
            content = re.sub(
                rf"\bimport {re.escape(old_import)}\b", f"import {new_import}", content
            )

        if content != original:
            filepath.write_text(content)
            return 1
        return 0
    except Exception as e:
        print(f"✗ {filepath}: {e}")
        return 0


# Find all Python files in backend/
backend_dir = Path("backend")
fixed_files = 0

for py_file in backend_dir.rglob("*.py"):
    if fix_imports_in_file(py_file):
        print(f"✓ {py_file}")
        fixed_files += 1

print(f"\n✅ Fixed imports in {fixed_files} files")
