# Consumers should name themselves — `x-aire-project` on every gateway call

Status: Done (2026-08-12, insult — same day)
Proposed: 2026-08-12 by Bernard (via the front's conversations view)

## What it is

The gateway mirror already records `x-aire-project` per exchange
(`gateway_mirror.py`), and the front's `/gateway` view now groups turns into
conversations with an **app** column — but only 1 of 244 logged rows ever
carried the header, so the column reads `—` for every real conversation.
The protocol exists; the consumers don't speak it.

The ask: every app pointed at the gateway sends `x-aire-project: <its-name>`
(insult first — its Alex/Insult conversations are the door's real traffic
today). One static header in each consumer's client config.

## Canonical path to reuse (Art. 6)

Nothing new on AIRE's side — the header is consumed in `gateway.py`, stored by
`gateway_mirror.py`, rendered by `front/app/gateway/page.tsx`. The change
lives in each CONSUMER repo (discord-bot for insult): add the header where
`ANTHROPIC_BASE_URL` is already pointed at the gate. Claude Code callers can
set it via `ANTHROPIC_CUSTOM_HEADERS`.

## The decision that's the owner's

Whether the header should eventually be REQUIRED for invited keys (a lent
credential with no self-declared name is harder to audit) — that tightens the
lending contract (#32) and is Bernard's call, not a default.

## Status / next step

**Done for insult, 2026-08-12.** The caller turned out to be `persona-runner`
(the Container App whose live env already pointed `ANTHROPIC_BASE_URL` at the
gate — set out-of-band, recorded nowhere). Shipped as:

- Mechanism proven first with a local smoke turn: `ANTHROPIC_CUSTOM_HEADERS=
  "x-aire-project: smoke-33" claude -p` through the gate → the request row
  landed with `project = smoke-33`.
- `az containerapp update` set `ANTHROPIC_CUSTOM_HEADERS=x-aire-project: insult`
  on persona-runner; revision 0000161 Healthy at 100% traffic.
- Both env vars recorded in discord-bot's DR runbook (`docs/runbook_dr.md`,
  commit `c8edd30` v4.32.55) — `dr_inventory.sh` does not capture env vars and
  its gotcha 2 already bit once.
- Receipt on the real surface: a `POST /v1/turn` smoke through the runner
  produced a gateway request row with `project = insult`, and the front's
  `/gateway` app column renders it in production.

Open: other consumers (og118, future invited keys) still anonymous — add the
header where each one points at the gate. The "required for invited keys"
tightening stays Bernard's call.
