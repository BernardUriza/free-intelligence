# 53 — provider × access_mode: one credential rotor for both providers

Status: **Done 2026-10-27** — engine, both backends, the Mac installer, tests, the gpt-6 price rows
(PR #590), and both Codex slots armed on the Mac with live receipts: a plan turn (`metered=f`) and a
real turn through `codex/apikey/fallback` (`metered=t`, 0.1315 USD banked). What is still unmeasured
is the wording of a REAL exhausted plan (see Open).
Proposed: 2026-10-27 by Bernard (*"provider es una cosa y access_mode es otra con solo dos tipos, oauth y apikey"*),
after reading that the Codex backend (#52) has a single implicit credential and no fallback while the Claude
backend has a three-slot rotor (#31).

## What was wrong (read in the code, 2026-10-27, before this card)

- `engine/credentials.py` knew ONE provider. `CHAIN` was three Claude slots (`oauth-primary`, `oauth-backup`,
  `api-key-fallback`), and `is_metered()` decided by slot *name*. `Slot` was `(name, env)`.
- `agent_sdk/codex_process.py` started `codex exec` with the inherited environment and nothing else: the only
  credential was whatever `codex login` left in `~/.codex/auth.json`. If the ChatGPT plan hit its limit the
  turn failed; nothing rotated, nothing was marked `CREDENTIAL-EXHAUSTED`.
- Backlog #52 line 11 promised "metered tokens only as fallback" for OpenAI turns. Not implemented.

So `provider` and *how we are allowed in* were tangled: the Claude rotor was really a list of
`(access_mode, account)` pairs with the provider hard-coded, and Codex had the pair hard-coded too.

## The shape (as shipped)

Two orthogonal axes, both closed. Nothing else is a credential concept.

```python
@dataclass(frozen=True)
class Slot:
    name: str              # "claude/oauth/primary", "codex/apikey/fallback" — provider/mode/label
    provider: str          # "claude" | "codex": which backend speaks (ACP roster names ride "claude")
    access_mode: str       # "oauth" | "apikey": a seat on a plan, or a metered key
    env: dict[str, str]    # exactly what the spawned process needs, nothing more
    metered -> bool        # access_mode == "apikey"; replaced is_metered(slot_name) everywhere
```

One `CHAIN` table, ordered oauth before apikey inside each provider:

| provider | access_mode | arming env var | env handed to the process |
|---|---|---|---|
| claude | oauth | `CLAUDE_CODE_OAUTH_TOKEN`, `…_BACKUP` | `CLAUDE_CODE_OAUTH_TOKEN=<v>`, `ANTHROPIC_API_KEY=""` |
| claude | apikey | `ANTHROPIC_API_KEY_FALLBACK` | `ANTHROPIC_API_KEY=<v>`, `CLAUDE_CODE_OAUTH_TOKEN=""` |
| codex | oauth | `CODEX_HOME` (the plan's, written by `install-mac.sh`), `CODEX_HOME_BACKUP` | `CODEX_HOME=<dir>` |
| codex | apikey | `CODEX_API_KEY_FALLBACK` (`~/.secrets/aire-codex-api-key-fallback.txt`) | `CODEX_API_KEY=<v>` |

`Rotor` is one object keyed by provider: `rotor.active(provider)`, `rotor.burn(name, notice)`,
`rotor.all_dry(provider)` (no provider: any chain the box arms is dry — what `/health` reports and
costwatch alarms on). Each backend names the chain it rides (`CREDENTIALS = "claude" | "codex"`;
the ACP adapter rides `"claude"` because `claude-code-acp` spawns `claude`). `Birth.credential_env`
kept its name; `codex_process.start()` got the line it was missing, `env={**os.environ, **slot.env}`.
`engine/reset_clock.py` holds the reset-time parser (the rotor file hit the 150-line law).

What this deliberately does NOT do: no plugin registry, no per-provider strategy classes, no
"credential provider" abstraction. Two enums and one table. A third provider is a new row set.

## Measured against the real Codex CLI (0.164.0, 2026-10-27, bogus key, no money spent)

The original card assumed `OPENAI_API_KEY_FALLBACK → OPENAI_API_KEY` "which Codex honours and
skips the login". **False.** Four probes on an empty `CODEX_HOME`, then one on a copy of the plan's:

| probe | result |
|---|---|
| `OPENAI_API_KEY=sk-bogus`, empty home | `turn.failed`: *401 Missing bearer or basic authentication* — identical to no key at all: **ignored** |
| no key, empty home | same 401, no login prompt; the dir got its own sqlite files: **`CODEX_HOME` honoured** |
| `CODEX_API_KEY=sk-bogus`, empty home | `turn.failed`: *401 Incorrect API key provided: sk-bogus\*0000 … invalid_api_key* — a bearer was sent: **honoured** |
| `codex login --with-api-key` (stdin) into its own home | writes `auth.json` `{"auth_mode":"apikey","OPENAI_API_KEY":…}`; `exec` sends it. The sanctioned file path — not needed |
| `CODEX_API_KEY=sk-bogus` + the plan's `auth.json` in the SAME home | *invalid_api_key*: **the env var wins over the ChatGPT login**, so the apikey slot keeps the plan's `CODEX_HOME` and its thread store — a failover resumes the same thread |

Two consequences the card did not foresee:

- **A Codex limit is a `turn.failed`, not a lying success.** Its message now rides `TurnResult.error`
  (and `ResultMessage.error` through drain), never text — an error is not the persona's reply — and
  `limit_hit(result.error or result.text, usage)` burns the slot with the same predicate. The phrase
  table gained Codex's wording: `invalid_api_key` / `401 Unauthorized` measured live; `Usage limit
  reached`, `reached your usage limit`, `out of credits`, `rate limit reached`, `insufficient_quota` from
  the binary's string table. **A real exhausted plan is still unmeasured** — when it happens, read the
  `turn.failed` message off `aire_agent_log` and add the exact phrase.
- **Codex reports tokens, never dollars**, so "banks the turn as metered" needed a price. The backend
  prices every turn at OpenAI list through `pricing.openai_usd` (`prices.json` carries the gpt-6
  family at OpenAI's Standard tier since the same day; before that row `gpt-6-astra` billed at the
  dearest row, whose missing cache rate charged cached tokens at the full input price), cumulative per client like
  the SDK's `total_cost_usd` so the ledger's delta law holds. A plan turn now leaves an `aire_spend` row
  with `metered=false` (it left none before); a fallback turn leaves a real one.

## Acceptance (all green in `tests/`, 415 passing)

- `CHAIN` has no provider-specific code paths; `is_metered(name)` is gone, `slot.metered` is used everywhere
  (`turn._account`, the ledger gate, `Birth.metered`).
- A Codex turn with the plan exhausted rotates to `codex/apikey/fallback`, logs
  `CREDENTIAL-EXHAUSTED codex/oauth/primary` and banks the turn as metered —
  `test_a_plan_at_its_limit_rotates_to_the_metered_key_and_banks_it` runs it through `run_turn` with the
  real backend and a fake `codex` process that answers the limit wording until `CODEX_API_KEY` reaches it.
- A Claude turn behaves as before: #31's rotation and all-dry tests are green with the new names.
- `codex_process` is started with the slot's env: `last_env.json` from the fake process asserts
  `CODEX_API_KEY` and `CODEX_HOME` reached it.
- `arming.py` reports `credential_failover_<provider>` per provider the box arms;
  `credential_slots_armed` lists the new names (costwatch's `claude/oauth/backup` check updated).

## What changes on the boxes

- **The Mac**: `install-mac.sh` now writes `CODEX_HOME=$HOME/.codex` and, if
  `~/.secrets/aire-codex-api-key-fallback.txt` exists, `CODEX_API_KEY_FALLBACK=`. Until the installer
  re-runs, a `provider: "codex"` turn answers `credentials_exhausted` with *no credential slot is armed
  for provider 'codex'* — loud, not silent. The fallback key is Bernard's to mint (api.openai.com, a
  platform key; the Azure OpenAI key of #51 does not work there).
- **The droplet**: nothing — no Codex rows arm there; the `/health` guard is `credential_failover_claude`.

## Live receipt (the Mac, 2026-10-27 15:50Z, after PR #588 merged and `install-mac.sh` re-ran)

`/health` (owner view): `credential_slots_armed: ["codex/oauth/primary"]`, `credential_failover_codex: false`
in `disarmed` — the honest state, no fallback key on the box. One real turn through the door,
`POST /projects/videopipe/sessions/rotor53-095028/messages` `{"provider":"codex","mode":"complete"}`:
SSE `text` → `result` (`"pong"`, `model: gpt-6-astra`, `subtype: success`, `error: null`,
`total_cost_usd: 0.21177`) → `done`; `aire_spend` got its row: `engine | 0.21177 | metered=f | 1933 in |
12160 cache_read`. The 0.21 was the dearest-row price for a model then absent from `prices.json`
(cached tokens at $10 instead of $1); the `gpt-6-astra` row (10 / 50 / 1 cached, OpenAI Standard tier,
developers.openai.com/api/docs/pricing read 2026-10-27) reprices that same pong at 0.10 — still
nominal, nobody billed, now the figure a `CODEX_API_KEY` turn would actually pay. Re-measured after
PR #590 deployed (16:39Z, session `rotor53-prices-103936`): `pong`, `total_cost_usd: 0.06611` =
5,370 × 10 + 12,160 × 1 + 5 × 50 per million, and `aire_spend` holds the same figure, `metered=f`.

## The fallback, armed (2026-10-27 17:01Z)

Bernard said *"Sí, ármalo"*. The key was minted in platform.openai.com (Personal Organization, Default
project, name `aire-codex-fallback (Mac, #53)`, tracking `key_RuwfMfyJuJzcuoWH`, expiration Never,
permissions All) and saved to `~/.secrets/aire-codex-api-key-fallback.txt`; `install-mac.sh` wrote
`CODEX_API_KEY_FALLBACK=` and `/health` now lists `credential_slots_armed: ["codex/oauth/primary",
"codex/apikey/fallback"]`, `credential_failover_codex: true`. The key answered `/v1/models` 200 with
`gpt-6-astra` in the list before it was armed.

**The receipt through the metered slot** — a plan limit cannot be staged, so the plan seat was
disarmed for one turn (`CODEX_HOME` dropped from `~/.aire/env`, agent kickstarted, `/health` showed
`["codex/apikey/fallback"]` alone), one `provider: "codex"` pong went through the door on session
`rotor53-fallback-110130`: `gpt-6-astra`, `success`, `total_cost_usd: 0.1315` (13,125 uncached input
at $10 + 5 output at $50 per million, a cold thread so nothing cached), and `aire_spend` holds
`0.13150 | metered=t`. Then `install-mac.sh` re-ran and both slots were armed again. The installer is
the only thing that touched the env on the way back, so the box is in its canonical state.

**The ceiling that already exists**: the key bills OpenAI's Pay-as-you-go credit, **2.38 USD on the
day it was created, auto-reload OFF** — when it reaches 0 OpenAI refuses the key (an `insufficient_quota`
`turn.failed`, which burns the slot like any limit). That is ~18 cold pongs; a sized fallback is a
feature, not a gap, and topping it up is Bernard's call at platform.openai.com → Billing.

## Open

- A real exhausted plan's `turn.failed` wording is still unmeasured (the phrases came from the binary's
  string table); when it happens, read it off `aire_agent_log` and add the exact phrase.
- Cache WRITES: OpenAI lists a cache-write rate for gpt-6-astra that `openai_usd` does not model (it
  prices the written tokens at the plain input rate). The real charge for the fallback pong may read
  slightly above the 0.1315 booked; compare the Billing page's credit balance against `aire_spend`
  after a few turns and, if it drifts, add `cache_write` to the row and the formula.
- #52's open item (videopipe calling AIRE) is what this makes survive a plan limit.
