#!/usr/bin/env python3.14
"""Migrate task_repository.py from CORPUS_PATH to locked_session_h5().

This script performs surgical replacement of all h5py.File(CORPUS_PATH)
instances with locked_session_h5(session_id, mode=X).

Author: AI Agent (Autonomous Remediation)
Date: 2025-12-07
"""

import re

# Read file
with open("backend/storage/task_repository.py") as f:
    content = f.read()

# Replace pattern: with h5py.File(CORPUS_PATH, "r") as f:
pattern_r = r'with h5py\.File\(CORPUS_PATH, "r"\) as f:'
replacement_r = 'with locked_session_h5(session_id, mode="r") as f:'
content = re.sub(pattern_r, replacement_r, content)

# Replace pattern: with h5py.File(CORPUS_PATH, "a") as f:
pattern_a = r'with h5py\.File\(CORPUS_PATH, "a"\) as f:'
replacement_a = 'with locked_session_h5(session_id, mode="a") as f:'
content = re.sub(pattern_a, replacement_a, content)

# Count replacements
count_r = len(re.findall(replacement_r, content))
count_a = len(re.findall(replacement_a, content))

print(f"Migrated {count_r} read operations")
print(f"Migrated {count_a} write operations")
print(f"Total: {count_r + count_a} migrations")

# Write back
with open("backend/storage/task_repository.py", "w") as f:
    f.write(content)

print("✅ Migration complete")
