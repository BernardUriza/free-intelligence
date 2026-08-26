"""The credential rotor (#31): an ordered chain of Anthropic credentials for
the engine's spawned CLIs. When the active slot burns its weekly pool — the
lying-green signature below, measured live 2026-08-07 — the engine rotates to
the next slot and retries the turn. A burned slot COOLS instead of dying: the
pool refills weekly, so an hourly probe heals the chain without a redeploy.

Chain order is fixed (subscription pools before metered), slots build from env
at startup and unset slots are skipped — the mechanism ships working with only
the primary present. Rotation state is in-memory only: it re-derives from the
first failed turn after a restart. The gateway door (#30) never uses this
chain — its auth is the caller's own, passed through.

The API-key slot works headless (verified 2026-08-07 with a bogus key against
the real CLI): with ANTHROPIC_API_KEY set and CLAUDE_CODE_OAUTH_TOKEN blanked,
the CLI dispatches straight to /v1/messages — no interactive approval prompt.
"""

import os
import re
import time
from dataclasses import dataclass, field

from ..listen.applog import _now, append

COOLDOWN_S = float(os.environ.get("AIRE_CREDENTIAL_COOLDOWN_S", "3600"))
LIMIT_PHRASE = re.compile(r"hit your (weekly|usage) limit|usage limit.*resets",
                          re.IGNORECASE)
CHAIN = (
    ("oauth-primary", "CLAUDE_CODE_OAUTH_TOKEN",
     "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
    ("oauth-backup", "CLAUDE_CODE_OAUTH_TOKEN_BACKUP",
     "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
    ("api-key-fallback", "ANTHROPIC_API_KEY_FALLBACK",
     "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"),
)


@dataclass(frozen=True)
class Slot:
    name: str
    env: dict[str, str] = field(default_factory=dict)


AMBIENT = Slot("ambient")


def is_metered(slot_name: str) -> bool:
    """Whether a slot's dollars are REAL. The oauth-* slots ride the Max
    subscription — their `total_cost_usd` is nominal, already paid, and must not
    move the process spend ceiling (counting it muted every persona for 16 hours
    on 2026-08-25 to protect money nobody was billed). The API-key slot bills
    the card; `ambient` (local dev, Keychain) is unknown, so it counts."""
    return not slot_name.startswith("oauth-")


def limit_hit(text: str | None, usage: dict | None) -> bool:
    """The burned-pool signature: the limit phrase AND all-zero usage. BOTH are
    required — a turn that merely TALKS about limits has nonzero tokens, and an
    empty result without the phrase is #23's budget cut, not this."""
    if not text or not LIMIT_PHRASE.search(text):
        return False
    return not any(v for v in (usage or {}).values() if isinstance(v, (int, float)))


class Rotor:
    """The ordered slots plus their cooldown state. With no slot configured
    (local dev: the CLI reads the macOS Keychain), the chain is one ambient
    slot that injects nothing — behavior is byte-identical to before #31."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        env = os.environ if environ is None else environ
        self.slots = [Slot(name, {inject: env[source], blank: ""})
                      for name, source, inject, blank in CHAIN
                      if env.get(source)] or [AMBIENT]
        self.cooling: dict[str, float] = {}

    def active(self) -> Slot | None:
        """The first slot not cooling; an expired cooldown re-qualifies its
        slot (the probe that heals the chain). None means all dry."""
        now = time.monotonic()
        for slot in self.slots:
            burned_at = self.cooling.get(slot.name)
            if burned_at is None or now - burned_at >= COOLDOWN_S:
                self.cooling.pop(slot.name, None)
                return slot
        return None

    def burn(self, name: str) -> None:
        """Mark a slot exhausted, VISIBLY — the failure is seen in the log like
        the whitelist's DENIED lines, never swallowed ([[log-is-the-truth]])."""
        self.cooling[name] = time.monotonic()
        line = f"{_now()} - CREDENTIAL-EXHAUSTED {name}"
        print(line, flush=True)
        try:
            append(line)
        except OSError:
            pass

    def cooling_names(self) -> list[str]:
        return sorted(self.cooling)

    def retry_after_s(self) -> int:
        now = time.monotonic()
        waits = [COOLDOWN_S - (now - burned_at) for burned_at in self.cooling.values()]
        return max(0, round(min(waits))) if waits else 0
