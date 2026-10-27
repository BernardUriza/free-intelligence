"""The credential rotor (#31, #53): one ordered chain of slots for the engine's
spawned agents, on two closed axes. `provider` is WHICH backend speaks (Claude's
SDK, OpenAI's Codex CLI); `access_mode` is HOW we are let in — a seat on a plan
(`oauth`: nominal dollars, a pool that refills) or a metered key (`apikey`: real
dollars, never resets). One table, no per-provider code path: a third provider
is a new row set, never a new class.

When the active slot burns its pool (the lying-green signature below), the
engine rotates to the next slot OF THE SAME PROVIDER and retries. A burned slot
COOLS instead of dying: the pool refills on a clock (`reset_clock.py`), so a
probe heals the chain without a redeploy. Unset rows are skipped — it ships with
only a primary present. Rotation state is in-memory, re-derived from the first
failed turn after a restart. The gateway door (#30) never uses this chain.

The Codex rows are what codex-cli 0.164.0 honours, measured 2026-10-27 with a
bogus key (backlog #53 has the receipts): `CODEX_API_KEY` wins over a ChatGPT
`auth.json` in the same `CODEX_HOME`, so a failover keeps the plan's threads;
`OPENAI_API_KEY` is ignored. They blank nothing (an EMPTY value is unmeasured)."""

import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field

from ..listen.applog import _now, append
from .reset_clock import reset_delay_s

COOLDOWN_S = float(os.environ.get("AIRE_CREDENTIAL_COOLDOWN_S", "3600"))
PROVIDERS = ("claude", "codex")
ACCESS_MODES = ("oauth", "apikey")
# Claude phrases each arrived as the TEXT of a zero-usage "successful" turn (09-03 .. 10-10);
# Codex phrases are its `turn.failed` wording: the 401 measured 2026-10-27, the rest from 0.164.0's string table.
LIMIT_PHRASE = re.compile(
    r"hit your (weekly|usage|session|org'?s monthly spend) limit|usage limit.*resets"
    r"|credit balance is too low|rate_limit_error|disabled claude subscription access"
    r"|oauth access token has been revoked|authentication_error|permission_error"
    r"|usage limit reached|reached your usage limit|out of credits|rate limit reached"
    r"|insufficient_quota|invalid_api_key|401 unauthorized",
    re.IGNORECASE)
# provider, access_mode, label, the env var that ARMS the row, the var the spawned
# process receives, and the sibling var blanked so the CLI cannot prefer the other mode.
CHAIN = (
    ("claude", "oauth", "primary", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
    ("claude", "oauth", "backup", "CLAUDE_CODE_OAUTH_TOKEN_BACKUP", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
    ("claude", "apikey", "fallback", "ANTHROPIC_API_KEY_FALLBACK", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"),
    ("codex", "oauth", "primary", "CODEX_HOME", "CODEX_HOME", ""),
    ("codex", "oauth", "backup", "CODEX_HOME_BACKUP", "CODEX_HOME", ""),
    ("codex", "apikey", "fallback", "CODEX_API_KEY_FALLBACK", "CODEX_API_KEY", ""),
)


@dataclass(frozen=True)
class Slot:
    """One credential: `name` is `provider/access_mode/label`, `env` is exactly
    what the spawned process needs and nothing more."""

    name: str
    provider: str = "claude"
    access_mode: str = "apikey"
    env: dict[str, str] = field(default_factory=dict)

    @property
    def metered(self) -> bool:
        """Whether this slot's dollars are REAL. An `oauth` slot rides a plan —
        its `total_cost_usd` is nominal, already paid, and must not move the
        process spend ceiling (counting it muted every persona for 16 hours on
        2026-08-25 to protect money nobody was billed). An `apikey` slot bills
        the card; `ambient` (local dev, Keychain) is unknown, so it counts."""
        return self.access_mode == "apikey"


AMBIENT = Slot("ambient", "claude", "apikey")


def armed_slots(environ: Mapping[str, str]) -> list[Slot]:
    """Every chain row whose arming variable is set, in chain order."""
    return [Slot(f"{provider}/{mode}/{label}", provider, mode,
                 {inject: environ[source], **({blank: ""} if blank else {})})
            for provider, mode, label, source, inject, blank in CHAIN if environ.get(source)]


def limit_hit(text: str | None, usage: dict | None) -> bool:
    """The burned-pool signature: the limit phrase AND all-zero usage. BOTH are
    required — a turn that merely TALKS about limits has nonzero tokens, and an
    empty result without the phrase is #23's budget cut, not this."""
    if not text or not LIMIT_PHRASE.search(text):
        return False
    return not any(v for v in (usage or {}).values() if isinstance(v, (int, float)))


class Rotor:
    """The ordered slots plus their cooldown state, keyed by provider. With no
    Claude slot configured (local dev: the CLI reads the macOS Keychain), that
    chain is one ambient slot that injects nothing — byte-identical to before
    #31. Codex has no ambient: its plan seat is armed by `CODEX_HOME` or absent."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        env = os.environ if environ is None else environ
        self.slots = armed_slots(env)
        if not any(slot.provider == "claude" for slot in self.slots):
            self.slots.insert(0, AMBIENT)
        self.cooling: dict[str, float] = {}

    def providers(self) -> tuple[str, ...]:
        """The providers with at least one slot, in chain order."""
        return tuple(dict.fromkeys(slot.provider for slot in self.slots))

    def active(self, provider: str = "claude") -> Slot | None:
        """The provider's first slot not cooling; a reached deadline re-qualifies
        its slot (the probe that heals the chain). None means that chain is dry."""
        now = time.monotonic()
        for slot in self.slots:
            if slot.provider != provider:
                continue
            until = self.cooling.get(slot.name)
            if until is None or now >= until:
                self.cooling.pop(slot.name, None)
                return slot
        return None

    def burn(self, name: str, text: str | None = None) -> None:
        """Mark a slot exhausted, VISIBLY — the failure is seen in the log like
        the whitelist's DENIED lines, never swallowed ([[log-is-the-truth]]).
        The slot cools until the reset its notice names, else COOLDOWN_S."""
        delay = reset_delay_s(text)
        source = "notice" if delay is not None else "default"
        delay = COOLDOWN_S if delay is None else delay
        self.cooling[name] = time.monotonic() + delay
        line = f"{_now()} - CREDENTIAL-EXHAUSTED {name} cools {round(delay)}s ({source})"
        print(line, flush=True)
        try:
            append(line)
        except OSError:
            pass

    def cooling_names(self) -> list[str]:
        return sorted(n for n, u in self.cooling.items() if time.monotonic() < u)

    def all_dry(self, provider: str | None = None) -> bool:
        """Every armed slot of a provider cooling — its turns are served nothing
        (silent 2.5 days on 2026-09-15: primary on its weekly reset, the card at
        $0). With no provider named: ANY chain this box arms is dry."""
        providers = self.providers() if provider is None else (provider,)
        return any(self.active(p) is None for p in providers)

    def retry_after_s(self) -> int:
        now = time.monotonic()
        waits = [until - now for until in self.cooling.values()]
        return max(0, round(min(waits))) if waits else 0
