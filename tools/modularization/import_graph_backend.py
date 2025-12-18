#!/usr/bin/env python3
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_IMPORT_FROM_RE = re.compile(r"^\s*from\s+backend\.(?P<mod>[a-zA-Z0-9_\.]+)\s+import\s+")
_IMPORT_RE = re.compile(r"^\s*import\s+backend\.(?P<mod>[a-zA-Z0-9_\.]+)(\s+|$)")


@dataclass(frozen=True)
class ImportHit:
    file: Path
    line_no: int
    line: str
    origin: str


def _is_excluded(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    if "venv" in parts or ".venv" in parts:
        return True
    if "tests" in parts or "test" in parts:
        return True
    if "__pycache__" in parts:
        return True
    return False


def _extract_origin(line: str) -> str | None:
    m = _IMPORT_FROM_RE.match(line)
    if m:
        return m.group("mod")

    m = _IMPORT_RE.match(line)
    if m:
        return m.group("mod")

    return None


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"
    out_dir = repo_root / "docs" / "modularization"
    out_dir.mkdir(parents=True, exist_ok=True)

    hits: list[ImportHit] = []

    for path in sorted(backend_root.rglob("*.py")):
        if _is_excluded(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")

        for idx, raw_line in enumerate(text.splitlines(), start=1):
            origin = _extract_origin(raw_line)
            if not origin:
                continue

            rel = path.relative_to(repo_root)
            hits.append(ImportHit(file=rel, line_no=idx, line=raw_line.rstrip("\n"), origin=origin))

    raw_lines_path = out_dir / "backend_import_lines.txt"
    raw_lines_path.write_text(
        "\n".join(f"{h.file}:{h.line_no}:{h.line}" for h in hits) + ("\n" if hits else ""),
        encoding="utf-8",
    )

    counts = Counter(h.origin for h in hits)
    counts_path = out_dir / "backend_import_origins_count.txt"
    counts_path.write_text(
        "\n".join(f"{count:7d} {origin}" for origin, count in counts.most_common()) + ("\n" if counts else ""),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
