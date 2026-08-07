# Credential failover — the engine survives a burned weekly pool

Status: Proposed
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

Mechanism buildable now; slots fill when Bernard mints them.

Related: #23 (the lying empty result — same detection family), #25 (cumulative
ceiling — governs the metered slot), #30 (the gateway door — explicitly out of
scope, its auth is the caller's).
