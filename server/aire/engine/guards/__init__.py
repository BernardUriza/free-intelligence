"""Deterministic safety nets — what the model decided does not get a vote.

Five files that always change together, which is why they are a folder: adding a
guard means touching `registry` and writing one sibling, and the git history of
this package shows those files moving in the same commits every time.

- `registry` — which guards exist, and the law that the wire may NAME one and
  never DEFINE one (the daemon is internet-open and runs as root).
- `exec` — running a list of them over one turn, and the observational contract
  the door consumes (`observe`).
- `drift` — the `antidrift` guard: persona character-integrity.
- `detect` — the pattern matching, vendored from fi-core and collapsed.

The typed contract (`Guard`, `GuardOutcome`) stays in `engine/contract.py` with
the engine's other typed results — a guard's outcome is one of the engine's
values, not this package's private shape. The PATTERNS live in
`aire/prompts/drift-patterns.json`: content a human iterates, not code.

`pipeline`/`invariants` are deliberately NOT here. A guard is a safety net; a
mutation stage is a cosmetic rewrite that ships. Folding them in would group by
category instead of by change, and they change on their own clock.
"""

from .registry import REGISTRY, UnknownGuard, clean_guards, resolve
from .run import guard_level, observe, run_guards

__all__ = ["REGISTRY", "UnknownGuard", "clean_guards", "guard_level", "observe",
           "resolve", "run_guards"]
