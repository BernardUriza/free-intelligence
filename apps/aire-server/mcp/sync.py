"""Push a directory tree into an AIRE corpus, or pull a corpus back as files (#55).

The working copy stays where a repo's hooks already read it (videopipe's
`corpus/`, `editorial/`), gitignored; AIRE holds the durable, versioned copy.
`push` sends every UTF-8 file, and the daemon appends a version only when the
text changed, so pushing a whole tree after one edit lands one version. `pull`
writes each live document back under its doc id. Binary files are skipped and
listed: a corpus holds text.

    sync.py push <dir> [--prefix corpus/] [--project videopipe] [--corpus research] [--dry-run]
    sync.py pull <dir> [--prefix corpus/] [--project videopipe] [--corpus research]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aire_gate as gate  # noqa: E402

MAX_BYTES = 1_000_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".DS_Store"}


def texts(root: Path) -> tuple[dict[str, str], list[str]]:
    """Every UTF-8 file under `root` by its relative path, and what was skipped."""
    found: dict[str, str] = {}
    skipped: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(f"{rel} (binary)")
            continue
        if not body.strip() or len(body.encode("utf-8")) > MAX_BYTES:
            skipped.append(f"{rel} ({'empty' if not body.strip() else 'over 1 MB'})")
            continue
        found[rel] = body
    return found, skipped


def push(root: Path, base: str, prefix: str, http: gate.Http = gate.call, dry: bool = False) -> dict:
    found, skipped = texts(root)
    changed: list[str] = []
    for rel, body in found.items():
        if dry:
            continue
        landed = http("POST", f"{base}/documents", {"doc_id": prefix + rel, "text": body})
        if landed.get("changed"):
            changed.append(prefix + rel)
    return {"files": len(found), "changed": changed, "skipped": skipped, "dry_run": dry}


def pull(root: Path, base: str, prefix: str, http: gate.Http = gate.call) -> dict:
    written: list[str] = []
    resolved = root.resolve()
    for doc in http("GET", f"{base}/documents")["documents"]:
        doc_id = doc["doc_id"]
        if not doc_id.startswith(prefix):
            continue
        target = (root / doc_id[len(prefix):]).resolve()
        if resolved not in target.parents:
            raise ValueError(f"{doc_id!r} would land outside {root}")
        text = http("GET", f"{base}/text/{gate.quote(doc_id)}")["text"]
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            written.append(doc_id)
    return {"written": written}


def run(argv: list[str], http: gate.Http = gate.call) -> int:
    ap = argparse.ArgumentParser(prog="sync.py")
    ap.add_argument("verb", choices=("push", "pull"))
    ap.add_argument("dir", type=Path)
    ap.add_argument("--prefix", default="")
    ap.add_argument("--project", default=os.environ.get("AIRE_PROJECT", ""))
    ap.add_argument("--corpus", default=os.environ.get("AIRE_CORPUS", ""))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not (a.project and a.corpus):
        ap.error("--project and --corpus are required (or AIRE_PROJECT / AIRE_CORPUS)")
    base = f"/projects/{gate.quote(a.project)}/corpus/{gate.quote(a.corpus)}"
    out = (push(a.dir, base, a.prefix, http, a.dry_run) if a.verb == "push"
           else pull(a.dir, base, a.prefix, http))
    import json
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
