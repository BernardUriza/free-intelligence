"""The thirty-line law's teeth (rule: .claude/rules/thirty-line-law.md).

Functions ≤ 30 lines, files ≤ 150. Exit 1 on any violation. Grandfathered
files pending backlog #19 are listed here and shrink as they are fixed —
removing an entry is part of fixing its file.
"""

import ast
import sys
from pathlib import Path

MAX_FUNC, MAX_FILE = 30, 150
EXEMPT = {
    "aire/store.py",  # upstream-diffable SDK copy — the rule's one exception
}


def check(path: Path) -> list[str]:
    src = path.read_text()
    bad = []
    if (n := src.count("\n")) > MAX_FILE:
        bad.append(f"{path}: {n} lines (max {MAX_FILE})")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            span = node.end_lineno - node.lineno + 1
            if span > MAX_FUNC:
                bad.append(f"{path}:{node.lineno} {node.name}() {span} lines (max {MAX_FUNC})")
    return bad


def main() -> int:
    # Anchored to THIS file, not the caller's cwd. Globbing relatively made the
    # gate print "all green" after checking ZERO files whenever it was run from
    # anywhere but server/ — a check that cannot go red proves nothing, and this
    # one hid two real violations on 2026-08-11 before it was caught.
    root = Path(__file__).resolve().parent.parent
    files = [p for p in sorted(root.glob("*.py")) + sorted((root / "aire").rglob("*.py"))
             if str(p.relative_to(root)) not in EXEMPT]
    if not files:
        print(f"the law found nothing to check under {root} — that is a broken gate, not a pass")
        return 1
    bad = [b.replace(f"{root}/", "") for p in files for b in check(p)]
    print("\n".join(bad) if bad else f"thirty-line law: all green ({len(files)} files)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
