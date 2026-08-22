# Credential failover — the engine survives a burned weekly pool
## Armed 2026-08-22 — the machine finally has fuel

The rotor shipped 2026-08-07 and held **one slot** for fifteen days: a failover
with nowhere to fail over to, reported honestly by `/health` as
`credential_failover: false` once #40 gave the guards a voice. Bernard struck
his own seal to fix it — [#34](34-meter-the-pass-through.md) had settled on
2026-08-17 that no metered key would be minted while the door had no users but
him, and only he can strike a kill-list entry (Art. 7).

What was built, in this order on purpose — the cap before the credential:

- A workspace of its own, `aire` (`wrkspc_01EbZKjsjeBp4sBwGLtqRvsR`), so AIRE's
  spend is countable apart from Fénix's, which lives in `Default`. A credential
  is scoped to the surface it was handed to.
- A **$200/month spend limit on that workspace**, set before the key existed.
- The key `aire-failover-slot3`, **expiring NEVER, deliberately**: `arming.py`
  checks the variable is SET, not that the key is VALID, so an expired one would
  report `credential_failover: true` while dead — the exact lying-green #40
  exists to kill. Revoking it in the console is visible; expiring is not.

Three ceilings, outermost first, and only the first two survive a restart:
**$5.29 in prepaid credits with auto-reload OFF** (the API stops at zero),
**$200/month on the workspace** (survives a credit top-up), and
`AIRE_MAX_SPEND_USD=20`, which resets on every restart (#25's known limit).

**Receipts.** The key was tested against `api.anthropic.com` before it was armed
— *"slot three alive"*, 13 in / 6 out — because a failover slot that cannot
dispatch is decoration. Then on the live droplet: `credential_slots: 2`,
`credential_failover: true`, and the only guard left disarmed is
`whitelist_enforce`, which is deliberate. The wiring itself had been proven
earlier with a dummy value: burning `oauth-primary` rotates to
`api-key-fallback`, and the two slots inject disjoint env sets, which is what
lets the API key dispatch headless.

**And the watchdog was corrected in the same breath.** costwatch DECLARED
`credential_failover` as accepted-off; leaving that there would have been worse
than never declaring it, because the guard is on now and a future loss of the
key must go red — a stale declaration would have answered "accepted, carry on"
to exactly the regression the watch exists to catch. Slot 2
(`CLAUDE_CODE_OAUTH_TOKEN_BACKUP`) stays empty, and stays a placebo until it
comes from a DIFFERENT seat: two tokens from one account share one weekly pool.

Status: **Mechanism shipped 2026-08-07** — rotor + detection + rotate-and-retry
+ real `credentials_exhausted` error live; the backup slots are EMPTY until
Bernard mints them (his atoms, below).
Proposed: 2026-08-07 by Bernard, minutes after living the failure: the droplet's
`CLAUDE_CODE_OAUTH_TOKEN` hit its weekly limit ("resets Aug 10, 8pm UTC") and
every engine turn went dead while `/health` stayed green. "Si esto pasa, debe
haber otro OAuth de respaldo."

## What it is

An ordered **credential chain** for the engine (the SDK door only — the gateway
door #30 is auth-pass-through and never uses AIRE's credential). When the active
credential's pool is exhausted, the engine rotates to the next one and retries
the turn; when all are exhausted, it emits a REAL error naming which credential
resets when — never a silent empty result.

```
CLAUDE_CODE_OAUTH_TOKEN            (primary — subscription seat A)
CLAUDE_CODE_OAUTH_TOKEN_BACKUP     (backup — a DIFFERENT seat/account, else worthless)
ANTHROPIC_API_KEY_FALLBACK         (last resort — metered, never resets, budget-capped)
```

## The failure signature (measured live, 2026-08-07)

A limit-hit turn does NOT error. It "succeeds" with:

- result text: `You've hit your weekly limit · resets Aug 10, 8pm (UTC)`
- usage all zeros, `total_cost_usd: 0`, no tool calls

Same lying-green family as #23 (the budget cap). Detection needs BOTH signals:
limit-phrase match AND zero usage — either alone is too fragile.

## The trap this design must dodge

**Two tokens minted from the same account share the same weekly pool.** A
"backup" OAuth from the same login burns out in the same hour as the primary.
The chain's value = the independence of its pools. Bernard's atoms: mint the
backup token from a different Team seat/account (`claude setup-token` under that
login), and decide whether a metered API key sits at the end of the chain.

## Design (the mechanism, buildable now with the slots empty)

1. **A rotor in `engine/`** (one concept, one file): ordered credentials built
   from env at startup; skips unset slots. Each entry = the env dict to inject
   into the spawned CLI (`CLAUDE_CODE_OAUTH_TOKEN=x` or `ANTHROPIC_API_KEY=y` —
   verify how the CLI treats `ANTHROPIC_API_KEY` in non-interactive/SDK mode
   before shipping that slot).
2. **Detection at the result seam** (where #23's budget detection already
   lives): limit-phrase + zero-usage → append a visible `CREDENTIAL-EXHAUSTED
   <name>` event ([[log-is-the-truth]]: the failure is SEEN, like the
   whitelist's DENIED lines), retire the pooled client, rotate, retry the turn
   once on the next credential.
3. **Cooldown, not tombstone:** an exhausted credential is retried after a
   cooldown (parse the reset time if cheap, else a fixed probe interval) — the
   pool refills weekly and the chain should heal without a redeploy.
4. **All dry → real error** (`credentials_exhausted`, SSE error event) naming
   the soonest reset. Red stays red; no empty-result lies.
5. **Durability (the [[device-verb-protocol]] model):** each slot is a
   `~/.secrets/` file composed into `/etc/aire/env` by `provision-do.sh` /
   `lib/secrets.sh`; a kill test resurrects the full chain. Rotation state is
   in-memory only — it re-derives from the first failed turn after a restart.
6. **Budget unchanged:** the API-key slot pays real money per token; it rides
   the existing engine budget caps (#23/#25) — no new spend law needed.

## Canonical path to reuse (Art. 6)

- `engine/options.py` — already owns the spawned CLI's env (the #30 scrub
  landed there); the rotor plugs into the same seam.
- `engine/pool.py` / the #23 retire-poisoned-client mechanism — rotation IS
  retirement plus a different env next spawn.
- `infra/lib/secrets.sh` — the compose-secrets pattern for new slots.

## The decision that's Bernard's

1. Mint the backup OAuth from a genuinely different seat/account (his browser
   atom; the mechanism ships with the slot empty and skips it until filled).
2. Whether a metered API key closes the chain, and which key (a dedicated one —
   not another project's).
3. Chain order stays subscription-first (free pool before paid tokens)?

## Status / next step

**Shipped 2026-08-07** (the mechanism; slots fill when Bernard mints them):

- `engine/credentials.py` — the rotor: chain from env (unset slots skipped;
  with none set, one ambient slot injects nothing — local Keychain auth
  untouched), `limit_hit` predicate (phrase AND all-zero usage), cooldown of
  `AIRE_CREDENTIAL_COOLDOWN_S` (default 1h — no English-date parsing of the
  reset phrase; the hourly probe heals the chain when the pool refills).
- `engine/turn.py` — the turn lifecycle at the result seam (#23's layer): a
  burned attempt suppresses its lying result, logs `CREDENTIAL-EXHAUSTED
  <slot>`, retires the poisoned client, cools the slot, retries once on the
  next one. All dry → SSE `error` `credentials_exhausted` with the cooling
  list and `next probe in <n>s`.
- `infra/lib/secrets.sh` + `provision-do.sh` — the two optional slots compose
  from `~/.secrets/aire-claude-oauth-backup.txt` and
  `~/.secrets/aire-api-key-fallback.txt`; a missing file skips the slot.
- **API-key slot verified headless** (2026-08-07, bogus key against the real
  CLI): with `ANTHROPIC_API_KEY` set and `CLAUDE_CODE_OAUTH_TOKEN` blanked the
  CLI dispatches straight to `/v1/messages` — no interactive approval. (A bad
  key rides the CLI's own 11-attempt retry backoff before failing; a valid one
  answers immediately.)
- Tests: `tests/test_credentials.py` — rotor ordering/skip-empty/cooldown/
  all-dry, the detection predicate both ways, rotate-and-retry over a faked
  drain, and the slot env composing with the #30 scrub.

Bernard's atoms unchanged: mint the backup OAuth from a DIFFERENT seat
(`claude setup-token` under that login), decide the metered key. The chain
activates each slot the moment its env var appears — no code change needed.

Related: #23 (the lying empty result — same detection family), #25 (cumulative
ceiling — governs the metered slot), #30 (the gateway door — explicitly out of
scope, its auth is the caller's).
