"""Consumer lanes: a door consumer bound to its OWN credential, off the shared
chain. The rotor's chain (#31) is ordered for the personas — subscription pools
first — and every consumer shares it, so a batchy judge that reviews twenty pull
requests in an afternoon burns the pool the personas need. On 2026-10-08 BAIR
did exactly that: four reviews of one migration emptied the primary's monthly
cap, and with the backup and the card dry the engine served nothing at all.

A lane names the consumer by the door token it presents and the credential it
spends. While the lane's credential is ARMED, that consumer's turns ride it
alone and never fall back to the pool: a dry lane is the consumer's problem,
reported as `credentials_exhausted`, never the personas'. While it is NOT armed
the consumer rides the shared chain exactly as before — shipping this changes
nothing until the key lands in `/etc/aire/env`.

The lane slot is metered (`api-key-*`): its dollars count against the process
ceiling and each client is born with the per-client cap. A review session lives
one turn, so the cap's poisoning never outlives the answer it follows."""

import hmac
import os
from typing import Any

from .credentials import Slot

# consumer → (the door token env that names it, the credential env it spends).
LANES = {
    "bair": ("AIRE_BAIR_TOKEN", "ANTHROPIC_API_KEY_BAIR"),
}


def armed(environ: dict[str, str] | None = None) -> dict[str, Slot]:
    """The lanes whose credential is present, as rotor slots. Built once at import
    like the bearer's tokens: the env file is read at boot, never mid-flight."""
    env = os.environ if environ is None else environ
    return {lane: Slot(f"api-key-{lane}", {"ANTHROPIC_API_KEY": env[cred],
                                           "CLAUDE_CODE_OAUTH_TOKEN": ""})
            for lane, (_, cred) in LANES.items() if env.get(cred)}


LANE_SLOTS = armed()


def lane_of(presented: str, environ: dict[str, str] | None = None) -> str:
    """The lane a presented door token belongs to, or "" (the shared chain).
    Constant-time per candidate, like the bearer check: no early exit."""
    env = os.environ if environ is None else environ
    found = ""
    for lane, (token_env, _) in LANES.items():
        token = env.get(token_env, "")
        if token and hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8")):
            found = lane
    return found


def pick(rotor: Any, lane: str, slots: dict[str, Slot] | None = None) -> Slot | None:
    """The slot this turn rides. An armed lane is exclusive — cooling means
    None (`credentials_exhausted`), never the pool. No lane, or a lane whose
    credential is absent: the shared chain, unchanged."""
    slot = (LANE_SLOTS if slots is None else slots).get(lane)
    if slot is None:
        return rotor.active()
    return None if slot.name in rotor.cooling_names() else slot
