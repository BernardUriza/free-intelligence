from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

DEFAULT_REDACT_RULES = [r"\b\d{5,}\b", r"\bCURP|RFC\b"]


def redact_text(text: str, redact_rules: Iterable[str] | None = None) -> str:
    """Redact all matches of redact_rules in text replacing with sha256:8 hash.

    Returns the redacted text.
    """
    if not text:
        return text

    rules = list(redact_rules) if redact_rules else DEFAULT_REDACT_RULES

    def _hash_match(m: re.Match) -> str:
        v = m.group(0)
        h = hashlib.sha256(v.encode()).hexdigest()[:8]
        return f"[REDACTED:{h}]"

    redacted = text
    for pattern in rules:
        try:
            redacted = re.sub(pattern, _hash_match, redacted, flags=re.IGNORECASE)
        except re.error:
            # If invalid regex, skip
            continue

    return redacted


def redact_and_hash_once(text: str, rules: Iterable[str] | None = None) -> tuple[str, dict]:
    """Redact text and return (redacted_text, metadata) where metadata contains
    original_length and a list of found_hashes.
    """
    redacted = redact_text(text, rules)
    # collect hashes present
    hashes = re.findall(r"\[REDACTED:([0-9a-fA-F]{8})\]", redacted)
    return redacted, {"length": len(text), "hashes": hashes}
