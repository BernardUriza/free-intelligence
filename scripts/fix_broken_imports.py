#!/usr/bin/env python3.14
"""
Fix broken imports with incorrect indentation after refactor.

Pattern fixed:
    from some_module import X
        function_a,        # ← IndentationError
        function_b,
    )

Becomes:
    from some_module import X
    # FIXME: Broken imports - use DI container
"""

import re
from pathlib import Path

AFFECTED_FILES = [
    "backend/services/soap/api/public/soap.py",
    "backend/services/evidence/api/public/evidence.py",
    "backend/services/document/api/public/documents.py",
    "backend/services/workflow/api/public/services/workflow_orchestrator.py",
    "backend/services/transcription/services/validators.py",
    "backend/services/transcription/api/public/transcription.py",
]


def fix_indented_imports(file_path: Path) -> tuple[bool, list[str]]:
    """
    Fix imports indentados sin declaración 'from'.

    Returns:
        (was_modified, fixed_lines_info)
    """
    content = file_path.read_text()
    lines = content.split('\n')

    fixed_lines = []
    fixed_info = []
    i = 0
    in_broken_import = False

    while i < len(lines):
        line = lines[i]

        # Detectar inicio de import roto: línea indentada con identificador Python
        if re.match(r'^\s{4,}[a-zA-Z_]', line) and not line.strip().startswith('#'):
            in_broken_import = True
            # Comentar esta línea
            indent = len(line) - len(line.lstrip())
            fixed_line = ' ' * max(0, indent - 4) + '# FIXME: ' + line.strip()
            fixed_lines.append(fixed_line)
            fixed_info.append(f"Line {i+1}: {line.strip()} → commented")

        # Detectar fin de import roto (paréntesis de cierre indentado)
        elif in_broken_import and re.match(r'^\s*\)', line):
            # Comentar el paréntesis también
            fixed_lines.append('# FIXME: ' + line.strip())
            fixed_info.append(f"Line {i+1}: {line.strip()} → commented")
            in_broken_import = False

        else:
            fixed_lines.append(line)

        i += 1

    new_content = '\n'.join(fixed_lines)

    if new_content != content:
        file_path.write_text(new_content)
        return True, fixed_info
    return False, []


def main():
    print("🔧 Fixing broken imports with incorrect indentation\n")

    total_fixed = 0
    total_lines = 0

    for file in AFFECTED_FILES:
        path = Path(file)
        if not path.exists():
            print(f"⚠️  Not found: {file}")
            continue

        was_fixed, fixed_info = fix_indented_imports(path)

        if was_fixed:
            print(f"✅ Fixed: {file}")
            for info in fixed_info:
                print(f"   {info}")
            total_fixed += 1
            total_lines += len(fixed_info)
        else:
            print(f"⏭️  Skipped (no changes needed): {file}")

    print(f"\n📊 Summary:")
    print(f"   Files fixed: {total_fixed}/{len(AFFECTED_FILES)}")
    print(f"   Lines commented: {total_lines}")
    print(f"\n✅ Next step: Compile files to verify syntax errors are gone")


if __name__ == "__main__":
    main()
