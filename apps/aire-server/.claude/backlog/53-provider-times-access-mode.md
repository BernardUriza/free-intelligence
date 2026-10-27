# 53 — provider × access_mode: one credential rotor for both providers

Status: **In progress** — shipped 2026-10-27 (engine, both backends, the Mac installer, tests);
the live receipt on the Mac door rides the oauth seat, the apikey failover is proven by the
E2E test against the real `codex exec` shapes and stays unarmed until a key file exists.
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
  prices every turn at OpenAI list through `pricing.openai_usd` (`gpt-6-astra` is absent from
  `prices.json`, so it bills at the dearest row — the table's deliberate bias), cumulative per client like
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
12160 cache_read`. The 0.21 is the dearest-row price for a model absent from `prices.json` — nominal,
nobody billed; a `gpt-6-astra` row with OpenAI's list price would make the nominal figure honest too.

## Open

- The live receipt of the apikey failover needs a platform key in the file above, or a real exhausted plan.
- `prices.json` has no `gpt-6-astra` row: plan turns are priced at the dearest row (nominal, but inflated).
- #52's open item (videopipe calling AIRE) is what this makes survive a plan limit.
