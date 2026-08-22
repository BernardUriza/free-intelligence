"""The guard registry — per-turn safety nets selected by NAME, never by spec.

A TOOL (`tools.py`) is OPTIONAL: a capability the model *may* call. A GUARD is a
GUARANTEE: it runs on the turn's text with no model discretion. An anti-drift
check that must sanitize an identity leak before it ships, or a triage that must
escalate regardless of the model's phrasing, belongs here.

Same law as the tool registry, for the same reason: the daemon is internet-open
and runs as root, so a turn may NAME a guard from this vetted set and never
DEFINE one. The wire carries `{"guards": ["antidrift"]}` — no patterns, no
callables, no regex a stranger could turn into a ReDoS against a paid turn.

Copied from fi-runner's `guards.py`, which already owned this contract, stripped
of every fi-runner dependency. Each factory imports its fi-core backing LAZILY
(fi-core is not on PyPI, so the droplet carries no hard dependency): a guard
nobody names costs nothing, and naming one without fi-core installed fails loudly
at build time instead of silently at inspect time.

Named `guard_registry`, not `guards`: `listen/guards.py` already owns that name
for the socket's flood and whitelist gates. Two unrelated concepts may not share
a filename in one repo — a traceback has to identify which one it means.

The typed contract itself — `Guard`, `GuardOutcome` — lives in `contract.py` with
the engine's other typed results; running a list of them, and reading a level off
what they found, lives in `guard_exec.py`.
"""

from __future__ import annotations

from typing import Any

from .contract import Guard
from .guard_drift import build_antidrift

REGISTRY: dict[str, Any] = {
    "antidrift": build_antidrift,
}


class UnknownGuard(Exception):
    """A requested guard name is not in the vetted registry."""


def clean_guards(names: Any) -> list[str]:
    """Validate the door's `guards` field into a deduped list of known registry
    names. Anything else — a dict, a pattern, a non-string, an unknown name — is
    refused: the wire may only NAME a guard, and only one AIRE ships."""
    if not names:
        return []
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise UnknownGuard("guards must be a list of registry names (strings)")
    out: list[str] = []
    for n in names:
        if n not in REGISTRY:
            raise UnknownGuard(f"unknown guard {n!r}; available: {sorted(REGISTRY)}")
        if n not in out:
            out.append(n)
    return out


def resolve(names: list[str]) -> list[Guard]:
    """Build the vetted guards for the given names. Each factory pulls its fi-core
    backing only when called, so an unnamed guard never imports anything."""
    return [REGISTRY[name]() for name in names]
