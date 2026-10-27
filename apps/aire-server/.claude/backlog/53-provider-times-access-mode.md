# 53 — provider × access_mode: one credential rotor for both providers

Status: **Proposed**
Proposed: 2026-10-27 by Bernard (*"provider es una cosa y access_mode es otra con solo dos tipos, oauth y apikey"*),
after reading that the Codex backend (#52) has a single implicit credential and no fallback while the Claude
backend has a three-slot rotor (#31).

## What is wrong today (read in the code, 2026-10-27)

- `engine/credentials.py` knows ONE provider. `CHAIN` is three Claude slots (`oauth-primary`, `oauth-backup`,
  `api-key-fallback`), and `is_metered()` decides by slot *name*. `Slot` is `(name, env)`.
- `agent_sdk/claude.py` receives the rotor's `credential_env` through `engine/options._env`.
  `agent_sdk/codex_process.py` starts `codex exec` with the inherited environment and nothing else: the
  only credential is whatever `codex login` left in `~/.codex/auth.json`. If the ChatGPT plan hits its
  limit the turn fails; nothing rotates, nothing is marked `CREDENTIAL-EXHAUSTED`.
- `openai_gateway.py` (#51) holds an Azure OpenAI key, but only to lend it on `/openai/v1`. No AIRE
  backend can spend it.
- Backlog #52 line 11 promises "metered tokens only as fallback" for OpenAI turns. Not implemented.

So `provider` and *how we are allowed in* are tangled: the Claude rotor is really a list of
`(access_mode, account)` pairs with the provider hard-coded, and Codex has the pair hard-coded too.

## The shape

Two orthogonal axes, both closed enums. Nothing else is a credential concept.

```python
Provider   = Literal["claude", "codex"]          # which backend speaks (ACP roster names stay separate)
AccessMode = Literal["oauth", "apikey"]          # how we are let in: a seat on a plan, or a metered key

@dataclass(frozen=True)
class Slot:
    name: str              # "claude/oauth/primary", "codex/apikey/fallback" — provider/mode/label
    provider: Provider
    access_mode: AccessMode
    env: dict[str, str]    # exactly what the spawned process needs, nothing more

    @property
    def metered(self) -> bool:      # replaces is_metered(slot_name)
        return self.access_mode == "apikey"
```

One `CHAIN` table, four kinds of row, ordered oauth before apikey inside each provider:

| provider | access_mode | source env var | env handed to the process |
|---|---|---|---|
| claude | oauth | `CLAUDE_CODE_OAUTH_TOKEN`, `…_BACKUP` | `CLAUDE_CODE_OAUTH_TOKEN=<v>`, `ANTHROPIC_API_KEY=""` |
| claude | apikey | `ANTHROPIC_API_KEY_FALLBACK` | `ANTHROPIC_API_KEY=<v>`, `CLAUDE_CODE_OAUTH_TOKEN=""` |
| codex | oauth | `CODEX_HOME` (default `~/.codex`; `CODEX_HOME_BACKUP` for a second plan) | `CODEX_HOME=<dir>` |
| codex | apikey | `OPENAI_API_KEY_FALLBACK` | `OPENAI_API_KEY=<v>` (Codex CLI honours it and skips the login) |

`Rotor` stays one object, keyed by provider: `rotor.active(provider)`, `rotor.burn(slot)`,
`rotor.all_dry(provider)`. `limit_hit` gains a second phrase table for Codex's wording (to be
read from a real exhausted run, not guessed). `Birth.credential_env` keeps its name and type;
`codex_process.start()` gets the one line it is missing: `env={**os.environ, **credential_env}`.

What this deliberately does NOT do: no plugin registry, no per-provider strategy classes, no
"credential provider" abstraction. Two enums and one table. A third provider is a new row set,
not a new class.

## Acceptance

- `CHAIN` has no provider-specific code paths; `is_metered(name)` is gone, `slot.metered` is used everywhere
  (`spend.bank`, `aire_spend.metered`, the log line).
- A Codex turn with the plan exhausted rotates to `codex/apikey/fallback`, logs
  `CREDENTIAL-EXHAUSTED codex/oauth/primary` and banks the turn as metered.
- A Claude turn behaves byte-for-byte as before (#31's kill test and rotation test still green).
- `codex_process` is started with the slot's env in a test that asserts `OPENAI_API_KEY` reaches it.
- `arming.py` reports `credential_failover` per provider.

## Blocked by

Nothing technical. Ordering: #52's open item (videopipe calling AIRE) first, because that is what
blocks a video today; this refactor is what makes that call survive a plan limit.
