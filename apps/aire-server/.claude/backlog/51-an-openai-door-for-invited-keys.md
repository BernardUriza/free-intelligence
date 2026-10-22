# 51 — An OpenAI door for invited keys (Azure OpenAI, lent and metered like #32)

Status: **In progress** — the upstream exists and answers (2026-10-22); the door is not written.
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

## Next step

Write the door with the real invited-key test from #32 as the template: an invited
turn that relays, banks its cost and is refused once over its ceiling.
