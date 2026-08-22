"""Deterministic character-drift detection — vendored from fi-core, collapsed.

AIRE copies rather than imports, the same call the engine made and for the same
reason: fi-core is not on PyPI, and the droplet must not depend on a repo another
agent edits. What arrived is ~150 lines of regex matching whose only dependency
is `re`.

Collapsed on the way in. fi-core ships THREE detector classes — `BreakDetector`,
`AntiPatternMonitor`, `ClarificationDumpDetector` — whose `detect` bodies are
byte-identical and differ only in a severity label. Copying that triplication
into a clean repo would be importing a defect along with the feature, so it is
one class carrying its severity. The `check()`/`DetectionResult` surface came
along with no consumer on this side and did not survive the trip.

The PATTERNS are not here: they are content a human iterates (`prompts/
drift-patterns.json`), loaded at call time so editing them needs no redeploy —
[[prompts-as-content-not-code]].
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PATTERNS_FILE = Path(__file__).resolve().parent.parent / "prompts" / "drift-patterns.json"

_CACHE: dict[str, Any] = {"mtime": None, "data": None}


def packs() -> dict[str, Any]:
    """The pattern packs, re-read when the file changes. A tone fix is an edit,
    not a deploy — but a running turn must not pay for a stat on every call, so
    the parse is cached against the file's mtime."""
    mtime = PATTERNS_FILE.stat().st_mtime
    if _CACHE["mtime"] != mtime:
        _CACHE["data"] = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
        _CACHE["mtime"] = mtime
    return _CACHE["data"]


def compiled(key: str) -> list[re.Pattern[str]]:
    """One pack, compiled. A pattern that does not compile is DROPPED and named
    on stderr rather than killing the turn: an unusable rule must not disarm the
    rules beside it."""
    out: list[re.Pattern[str]] = []
    for src in packs().get(key, []):
        try:
            out.append(re.compile(src))
        except re.error as exc:
            print(f"DRIFT-PATTERN-BAD {key}: {src!r} ({exc})", flush=True)
    return out


@dataclass
class Detector:
    """One failure mode's patterns, and the label its matches carry.

    `severity` is what the caller routes on: `break` is a hard identity leak
    (retry-worthy), `clarification_dump` is the model punting the task back
    (soft), `soft_drift` is generic-assistant tone (telemetry only, never a
    retry — a retry storm over "great question!" costs more than the tic)."""

    patterns: list[re.Pattern[str]]
    severity: str = "unspecified"

    def detect(self, text: str) -> list[str]:
        """The source strings of every pattern that fired. Empty means clean."""
        return [p.pattern for p in self.patterns if p.search(text)]


def sanitize(text: str, patterns: list[re.Pattern[str]]) -> str:
    """Drop the sentences carrying a match — last-resort cleanup, only after a
    retry already failed. If EVERY sentence matches, the original is returned
    rather than an empty string: erasing the whole answer is a worse failure than
    shipping a flawed one, and the caller is the one who gets to decide."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = [s for s in sentences if not any(p.search(s) for p in patterns)]
    result = " ".join(kept).strip()
    return result or text
