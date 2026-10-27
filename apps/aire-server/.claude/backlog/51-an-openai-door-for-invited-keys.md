# 51 — An OpenAI door for invited keys (Azure OpenAI, lent and metered like #32)

Status: **Done 2026-10-26** — one real invited turn through `https://gate.bernarduriza.com/openai/v1/chat/completions` answered 200 from `gpt-5.4-mini-2026-03-17` and banked against the key's ceiling (`aire_token.spent_usd` for `visalaw-judge` = 0.0001005 after three turns: 14/7, 9/5, 9/5 tokens at $0.75/$4.50 per million — list price to the cent). Open, Bernard's: the judge's wiring on the Windows box. The ceiling per invitation is a route since PR #580 (`POST /access/ceiling`, owner token only); `visalaw-judge` raised to 5 USD on 2026-10-26.
Proposed: 2026-10-22 by Bernard (*"quisiera hacer uno nuevo para que también yo pueda ofrecerle el servicio de OpenAI a mis clientes de AIRE"*).

## What exists (2026-10-22, verified)

- Azure resource `aire-openai` in `og118-rg` (eastus2, S0). Endpoint
  `https://bu-aire-openai.openai.azure.com/` — the subdomain `aire-openai` is taken
  globally by someone else's resource.
- Deployment `gpt-5.4-mini` (2026-03-17, GlobalStandard, **20K TPM**). The TPM is the
  physical rate ceiling: no caller can burn tokens faster than that, whatever AIRE does.
- Key in `~/.secrets/aire-openai-azure.txt` (endpoint, key, deployment). Not on the
  droplet yet: nothing reads it.
- Real call `POST /openai/v1/chat/completions` → HTTP 200, `pong`, 15 tokens.
- Budget `aire-openai-10usd` (Cost Management, scoped to this resource only): mail
  to bernarduriza@gmail.com at 50% and 100% actual, and 100% forecast. **A budget
  ALERTS, it never stops** — the stop is the per-key ceiling below.

## Why it is not just "give them the key"

`insult-openai` cost USD 81 in eight days (2026-10-02..09) on gpt-4.1 input tokens
and nobody saw it until the invoice. Azure has no prepaid balance: the #49 law
("a $0 balance is the spend cap") cannot hold here, so the cap must be AIRE's own.
That is exactly what the gateway already does for Anthropic (#32): the invited key
never sees the credential, every turn is priced from tokens and charged against the
invitation's ceiling.

## The shape (reuse, not a second gateway)

1. A door `POST /openai/v1/chat/completions` (and `/responses` if a client needs it)
   beside `/v1/messages`, same invited-key auth, same `aire_spend` ledger.
2. `lending.py` grows a second named slot `AIRE_LEND_AZURE_OPENAI_*` — its own
   variables, revocable alone, never the engine's (the #32 two-roles-two-keys law).
3. `prices.json` gains OpenAI rows; `pricing.py` learns OpenAI's usage shape
   (`prompt_tokens`, `cached_tokens`, `completion_tokens`, reasoning counted as
   output). An unknown model is still charged at the dearest rate.
4. Mirror into the gateway log like any relayed turn; SSE relayed byte for byte.
5. Pass-through for a caller with their own OpenAI key is NOT in scope: the point is
   to sell Bernard's access.

## The decisions that are the owner's

- Which models clients get (only `gpt-5.4-mini` is deployed; each extra one is a
  `deployment create`, $0 idle).
- The price to the client (markup over list) and each invitation's ceiling.
- Microsoft's Product Terms for Azure OpenAI are NOT read yet: before the first
  paying client, read what they say about serving third parties through AIRE.

## What shipped (2026-10-22)

- `POST /openai/v1/chat/completions` and `/openai/v1/responses` only; any other
  OpenAI path 404s, because a call this door cannot price would be free Azure money.
- Admission in `door._admit_openai`: an AIRE key as the Bearer (OpenAI SDK) or in
  `api-key` (Azure SDK); no pass-through, unknown 401, spent 402, slot 429.
- `lending.azure_openai()` / `lend_openai()`: `AIRE_OPENAI_UPSTREAM` +
  `AIRE_LEND_AZURE_OPENAI_KEY`, provisioned from `~/.secrets/aire-openai-azure.txt`.
- A streamed chat that did not ask for usage gets `stream_options.include_usage`.
- `pricing.openai_usd`: cache counted inside the input; `gpt-4.1` row $2/$8/$0.50.
- The relay is shared with #30 (`gateway.forward`); the mirror's pool became
  per-event-loop like `db.pool` (two servers in one process segfaulted under uvloop).
- First consumer: the Visalaw hooks' LLM judge, dead since `insult-openai` was
  deleted (2026-10-16). Azure refused `gpt-4.1` on `aire-openai` the first time
  with 715-123420 ("unusual activity").

## What shipped (2026-10-26)

- PR #576 carried the 2026-10-22 commits plus: `relay.py` (the relay both doors
  share; `gateway.py` had hit 158 lines against the 150 law), the Azure slot
  moved into `openai_gateway.py`, `prices.json` gained `gpt-5.4-mini`
  ($0.75/$4.50/$0.075 cached, GlobalStandard, the only deployment on
  `aire-openai`; without the row every turn priced at the dearest fallback),
  and `provision-do.sh` points the pen's firewall at `og118-rg`.
- Access requested for `visalaw-judge` through `/access/request` (gate answered
  `sent`); the approve mail is in Bernard's inbox.

## What shipped (2026-10-26, later)

- PR #578: the nothing-to-lend 503 moved into `_admit_openai`, before any slot is
  claimed (the Gatekeeper's note on #576).
- Env on the droplet (`AIRE_OPENAI_UPSTREAM`, `AIRE_LEND_AZURE_OPENAI_KEY`),
  `arming.report()` says `lending_openai: true`.
- `visalaw-judge` approved and minted; key in `~/.secrets/aire-key-visalaw-judge.txt`.
- The first real turn hit a wall that was not the door: the Azure subscription
  was `Warned`/read-only because the September invoice (G189632160, USD 163.22)
  went past due on 2026-10-09 with no payment method on the account. Azure
  answered 401 to a correct key; every container app and SWA was down with it.
  Paid 09:28 UTC, subscription `Enabled` 09:32, Azure OpenAI 200 the same
  minute. Memory: `azure-subscription-pastdue-2026-10`.
- Streamed turns carry usage because the door injects
  `stream_options.include_usage`; verified on the wire (9/5 tokens in the last
  chunk).

## Next step (the consumer, not the door)

Point the Visalaw hooks' judge at the door: `base_url =
https://gate.bernarduriza.com/openai/v1`, `api_key` = the `visalaw-judge` key
(`~/.secrets/aire-key-visalaw-judge.txt`, Bearer or `api-key`), `model =
gpt-5.4-mini`. The ceiling is no longer a re-approval: `POST /access/ceiling`
(PR #580, merged `973ce2dd`, deployed 2026-10-26) moves one live key's
`budget_usd` with `AIRE_AUTH_TOKEN` alone, spend untouched. `visalaw-judge`
sits at 5.00 USD since 2026-10-26 10:20 UTC (live receipt: 200
`{"nickname":"visalaw-judge","budget_usd":5.0,"spent_usd":0.0001005}`; the
canary token got 401). At $0.75/$4.50 per million that is on the order of a
thousand judge calls of a few thousand tokens.

## Second consumer (2026-10-27): `susurro-diarize`

The susurro gateway's `/v1/diarize` (ACA `susurro-rg`) had been calling the deleted
`insult-openai` deployment (`DIARIZE_OPENAI_ENDPOINT=https://northcentralus.api.cognitive.microsoft.com`,
answering 502 *"Diarize LLM 401: Access denied due to invalid subscription key"* to the ThinkPad).
`susurro-diarize` was requested through `/access/request` (owner token), approved from the mail's
link, minted 17:59Z, raised to 5 USD with `POST /access/ceiling`; key in
`~/.secrets/aire-key-susurro-diarize.txt`. Receipt: two diarize-shaped turns (system + user,
`temperature: 0.1`, `response_format: json_object`) → 200 from `gpt-5.4-mini-2026-03-17`, 21/11 tokens,
`aire_spend` 0.0000653 USD each, `metered=t`. **The door relays Azure's refusal of `max_tokens` on
gpt-5.4-mini** (400 `unsupported_parameter`, use `max_completion_tokens`): a consumer written for
gpt-4.1 must rename that field. The consumer's wiring landed the same day (susurro/master `4c92edf` + `aa9d85a`, backlog
`diarize-502` Done there): `_diarize_window` sends Bearer + `max_completion_tokens`, the Container
App points at `https://gate.bernarduriza.com/openai/v1`, and the secret was set from Bernard's Mac
(`az containerapp secret set` + revision restart, since a `secretRef` only resolves at container
start). Closing receipt 18:09:53Z: `POST /v1/diarize` on sus.bernarduriza.com → 200, four segments
labelled correctly, `engine: aire-gpt-5.4-mini`, `aire_spend` `gateway | susurro-diarize | 0.0010575 | metered=t`.

## Superseded steps (2026-10-26, kept for the record)

1. Bernard: run the env script (appends `AIRE_OPENAI_UPSTREAM` +
   `AIRE_LEND_AZURE_OPENAI_KEY` from `~/.secrets/aire-openai-azure.txt`,
   restarts `aire-server`). `provision-do.sh` cannot do it: both DigitalOcean
   tokens in `~/.secrets` answer 401 — regenerate one, or the next provision is
   by hand too.
2. Bernard: click approve in "AIRE — visalaw-judge wants in"; the key arrives in
   "AIRE — the key for visalaw-judge".
3. One real invited turn against gpt-5.4-mini, then `aire_token.spent_usd` for
   `visalaw-judge` must be > 0. Only then does this item flip.

## Third consumer (2026-10-27): `thinkpad-stop-judge`

The Stop judge of the Infios ThinkPad (agent-constitution `gates/stop-judge`, raw packet by
Bernard's decision, http transport to this door). Bernard ordered the door opened from the Mac
("ábrele la puerta de AIRE a thinkpad primero"): `/access/request` with the owner token → 200
`sent` 19:01Z → approve link from the mail → key minted (mail "AIRE — the key for
thinkpad-stop-judge") → `~/.secrets/aire-key-thinkpad-stop-judge.txt` on the Mac → `POST
/access/ceiling` 5.00 USD (200, spent 0.0). Smoke test from the Mac with the new key:
`/openai/v1/chat/completions`, `gpt-5.4-mini`, `max_completion_tokens` → 200 from
`gpt-5.4-mini-2026-03-17`, `PASS`, 40/4 tokens, ceiling re-read `spent_usd 9.6e-05`. Delivery:
the key mail was forwarded from Bernard's Gmail to his Infios inbox at 19:11Z (Bernard registered
that address in `.claude/destinatarios-canales.txt` the same turn; no bounce at 19:14Z); the
ThinkPad stores it as `KEY=…` in its own `~/.secrets/aire-key-thinkpad-stop-judge.txt`. Open, the
ThinkPad's: receipt of the mail, the local file, and the judge's four cases through the door.
