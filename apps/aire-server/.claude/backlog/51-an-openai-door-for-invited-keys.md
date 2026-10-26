# 51 — An OpenAI door for invited keys (Azure OpenAI, lent and metered like #32)

Status: **In progress** — DEPLOYED 2026-10-26 (PR #576, droplet on `abb4bc8d`; `/openai/v1/chat/completions` answers 401 `AIRE: unknown key` in OpenAI's error shape). Not yet usable: the droplet's `/etc/aire/env` lacks the two door variables, and no key is minted.
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

## Next step

1. Bernard: run the env script (appends `AIRE_OPENAI_UPSTREAM` +
   `AIRE_LEND_AZURE_OPENAI_KEY` from `~/.secrets/aire-openai-azure.txt`,
   restarts `aire-server`). `provision-do.sh` cannot do it: both DigitalOcean
   tokens in `~/.secrets` answer 401 — regenerate one, or the next provision is
   by hand too.
2. Bernard: click approve in "AIRE — visalaw-judge wants in"; the key arrives in
   "AIRE — the key for visalaw-judge".
3. One real invited turn against gpt-5.4-mini, then `aire_token.spent_usd` for
   `visalaw-judge` must be > 0. Only then does this item flip.
