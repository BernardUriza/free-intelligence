# CONVO-SYNC-1 — server-side conversations (cross-device chat sync), gated on adoption

Status: Proposed (deferred — adoption-gated)
Proposed: 2026-06-21 by Bernard

## What it is

When og118 has more users, move conversation persistence from purely client-side
(IndexedDB, local-first, per-origin, per-device) to a **server-side store**, so a
user's chats follow them across devices, browsers, and origins. Today the backend
is STATELESS by design (DD-002): the transcript lives only in the browser and the
client replays a recent window each turn. The consequence — same account on laptop
vs phone vs localhost vs staging sees DIFFERENT chats — is acceptable now (papelería,
low usage) but will surprise users once adoption grows and people expect their
history everywhere.

This is the conversation twin of [[proj-sync-1-backend-owned-projects]] (which does
the same for the Projects list): the server becomes the owner-keyed source of truth,
the local store becomes a cache.

## Two costs of today's local-first design this would fix

1. **No cross-device sync** — chats are local to each (origin × device × account).
2. **Sliding-window forgetting** — only the most recent ~20 msgs / 16k chars are
   replayed (`client_history_max_messages` / `client_history_max_chars` in the
   Runner); a long conversation loses its head. A server store + a pooled session
   could keep more context.
3. **No prompt cache** — history-replay re-sends the window each turn, forgoing the
   Anthropic prompt-cache benefit a pooled persistent session gets (insult_ai uses
   that pooled model). A server-side session would regain it.

## Canonical path to reuse (Art. 6)

The framework primitive ALREADY exists: `fi_runner.conversation.ConversationStore`
(InMemory + Redis-backed, with `max_messages` LTRIM). og118 deliberately REMOVED
its `InMemoryConversationStore` to be stateless. The future work is to wire a
DURABLE, **owner-keyed** ConversationStore (Postgres or Redis) back in — keyed by
the Auth0 `sub` (the same ownership boundary as Projects / PROJ-ACCOUNT) so it stays
per-account. Do NOT reinvent: extend the existing store contract; keep the
local-first IndexedDB as an offline cache layered on top.

## The decision that's the owner's (Art. 4)

- **WHEN to flip** — the adoption threshold. Bernard's call; do not build before
  real usage justifies the infra (a store + its ops) over the current zero-infra
  stateless design.
- **Local-first + server sync (dual) vs fully server-side** — whether the browser
  IndexedDB stays as an offline cache that reconciles with the server, or the
  server becomes the sole source. Architecture fork, Bernard's.

## Status / next step

Deferred on purpose. Today's local-first is the right call at current scale
(stateless backend → survives container recycle, zero infra, privacy: history
stays in the user's browser). Promote to *In progress* only when og118's usage
grows enough that cross-device chat history is a real user need. Keep the
`20 msgs / 16k chars` caps as-is until then.

Related: [[proj-sync-1-backend-owned-projects]] (the projects twin),
[[og118-identity-scoping-leak]] (the same owner-keyed boundary, client side).
