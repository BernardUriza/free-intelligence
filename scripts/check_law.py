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
    "aire/store.py",   # upstream-diffable SDK copy — the rule's one exception
    "aire/engine.py",  # grandfathered, backlog #19
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
    files = [p for p in sorted(Path(".").glob("*.py")) + sorted(Path("aire").rglob("*.py"))
             if str(p) not in EXEMPT]
    bad = [b for p in files for b in check(p)]
    print("\n".join(bad) if bad else "thirty-line law: all green")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
