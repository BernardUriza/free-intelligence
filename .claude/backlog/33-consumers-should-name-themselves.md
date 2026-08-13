# Consumers should name themselves — `x-aire-project` on every gateway call

Status: Proposed
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

Not started. Next step: one-line header in insult's gateway client config,
then watch the app column fill on `/gateway`.
