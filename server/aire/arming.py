"""Which guards are ARMED, and which are silently off.

Every guard in AIRE degrades politely when its knob is absent. No
``AIRE_MAX_SPEND_USD`` and the cumulative backstop never arms. No
``CLAUDE_CODE_OAUTH_TOKEN_BACKUP`` and the credential rotor is a one-slot chain
with nothing to fail over to. No ``AIRE_VERB_TOKEN`` and every MKDIR answers
DENIED. No ``AIRE_LEND_*`` and an invited key is told there is nothing to lend.
Each degradation is defensible alone. Together they are a lie, because
``/health`` answered ``{"status": "ok"}`` for every one of them — and a signal
that cannot go red proves nothing ([[verify-before-assuming]] Rule 22).

That is what this module ends. One place enumerates every guard and reports
whether it is armed, so a disarmed one is VISIBLE on the surface an operator
already watches instead of being discovered the day it was needed.

It reports STATE, never values: how many credential slots exist, never a token;
that a ceiling is set, never a DSN. Nothing here reads the database — it is the
process describing itself, not a waiter read ([[write-only-daemon]]).
"""

from __future__ import annotations

import os

# guard name → (what proves it armed, why its absence is not merely cosmetic)
_GUARDS: tuple[tuple[str, str], ...] = (
    # One database, one guard. `pen` and `store` watched AIRE_DATABASE_URL and
    # AIRE_DSN until 2026-08-22, when the two names turned out to be one value
    # copied by the provisioner — so /health implied two independent memories.
    ("database", "AIRE_DATABASE_URL"),
    # Armed means the env var is set, and for THIS guard that is all it can
    # mean: the counter behind it lives in RAM and is born at zero on every
    # restart (#25). The month's real figure rides beside this report as
    # `spend_month_usd`, read from `aire_spend` — alarm on that, not on this.
    ("spend_backstop", "AIRE_MAX_SPEND_USD"),
    ("turn_cap", "AIRE_MAX_BUDGET_USD"),
    ("verbs", "AIRE_VERB_TOKEN"),
    ("invitations", "AIRE_ACCESS_SECRET"),
    ("mail", "RESEND_API_KEY"),
)


def _credential_slots_armed() -> list[str]:
    """The rotor slots (#31) that actually carry fuel, by NAME and in chain
    order. A COUNT hid which slot was missing: primary + api-key-fallback is
    two slots, reads as "failover armed", yet the free second-Max `oauth-backup`
    can be empty — so a burned weekly pool rotates only to the metered card, and
    if that card is dry the turn dies with `credentials_exhausted`. Naming the
    armed slots makes an empty `oauth-backup` visible instead of masked by the
    count (2026-09-15)."""
    from .engine.credentials import CHAIN

    return [name for name, source, _, _ in CHAIN if os.environ.get(source)]


def _lending() -> bool:
    return bool(os.environ.get("AIRE_LEND_API_KEY") or os.environ.get("AIRE_LEND_OAUTH_TOKEN"))


def report() -> dict[str, object]:
    """Every guard's state, plus the disarmed ones gathered into one list an
    operator (or costwatch) can assert against without parsing the rest."""
    from .bearer import ACCEPTED_TOKENS

    armed: dict[str, bool] = {name: bool(os.environ.get(var)) for name, var in _GUARDS}
    armed["lending"] = _lending()
    armed["whitelist_enforce"] = os.environ.get("AIRE_WHITELIST_ENFORCE") == "1"
    armed["door_tokens"] = bool(ACCEPTED_TOKENS)
    slots = _credential_slots_armed()
    armed["credential_failover"] = len(slots) > 1
    return {
        "armed": armed,
        "disarmed": sorted(name for name, ok in armed.items() if not ok),
        "door_tokens": len(ACCEPTED_TOKENS),
        "credential_slots": len(slots),
        "credential_slots_armed": slots,
    }
