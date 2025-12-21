#!/usr/bin/env python3
"""Import Graph Analyzer.

Analyzes backend import dependencies and generates reports.

Usage:
    fi analysis import-graph
    fi analysis import-graph --output docs/modularization
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

_IMPORT_FROM_RE = re.compile(r"^\s*from\s+backend\.(?P<mod>[a-zA-Z0-9_\.]+)\s+import\s+")
_IMPORT_RE = re.compile(r"^\s*import\s+backend\.(?P<mod>[a-zA-Z0-9_\.]+)(\s+|$)")


@dataclass(frozen=True)
class ImportHit:
    """Single import hit in codebase."""

    file: Path
    line_no: int
    line: str
    origin: str


def _is_excluded(path: Path) -> bool:
    """Check if path should be excluded from analysis."""
    parts = {p.lower() for p in path.parts}
    if "venv" in parts or ".venv" in parts:
        return True
    if "tests" in parts or "test" in parts:
        return True
    return "__pycache__" in parts


def _extract_origin(line: str) -> str | None:
    """Extract import origin from line."""
    m = _IMPORT_FROM_RE.match(line)
    if m:
        return m.group("mod")

    m = _IMPORT_RE.match(line)
    if m:
        return m.group("mod")

    return None


def run(args: Sequence[str] | None = None) -> None:
    """Analyze backend import dependencies."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze backend import dependencies")
    parser.add_argument("--output", "-o", default="docs/modularization", help="Output directory")
    parsed = parser.parse_args(list(args or []))

    # Find repo root (go up from this file until we find .git)
    current = Path(__file__).resolve()
    repo_root = current
    while repo_root.parent != repo_root:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent

    backend_root = repo_root / "backend"
    out_dir = repo_root / parsed.output
    out_dir.mkdir(parents=True, exist_ok=True)

    hits: list[ImportHit] = []

    print(f"🔍 Analyzing imports in {backend_root}...")

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

    # Write raw lines
    raw_lines_path = out_dir / "backend_import_lines.txt"
    raw_lines_path.write_text(
        "\n".join(f"{h.file}:{h.line_no}:{h.line}" for h in hits) + ("\n" if hits else ""),
        encoding="utf-8",
    )
    print(f"📄 Wrote {len(hits)} import lines to {raw_lines_path}")

    # Write counts
    counts = Counter(h.origin for h in hits)
    counts_path = out_dir / "backend_import_origins_count.txt"
    counts_path.write_text(
        "\n".join(f"{count:7d} {origin}" for origin, count in counts.most_common())
        + ("\n" if counts else ""),
        encoding="utf-8",
    )
    print(f"📊 Wrote {len(counts)} unique origins to {counts_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Import Analysis Summary")
    print("=" * 60)
    print(f"Total imports: {len(hits)}")
    print(f"Unique origins: {len(counts)}")
    print("\nTop 10 imported modules:")
    for origin, count in counts.most_common(10):
        print(f"  {count:4d}  {origin}")


if __name__ == "__main__":
    run()
