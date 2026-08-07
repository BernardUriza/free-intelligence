# The gateway door — `POST /v1/messages`, so Claude Code points at AIRE

Status: Proposed
Proposed: 2026-08-07 by Bernard ("¿algún día voy a poder usar Claude Code pero
que en vez de pegarle al endpoint de Anthropic le pegue a este? ¿como si fuera
un Bedrock?")

## What it is

A second door on the daemon: an endpoint that speaks the **Anthropic Messages
API wire format** (`POST /v1/messages`, SSE), proxies each request straight to
`api.anthropic.com`, and mirrors both halves of the exchange into Postgres on
the way through. Any client that already knows how to talk to Anthropic — Claude
Code first — points at AIRE by env var and needs no other change.

The client half already exists and needs nothing built. Verified against the
Claude Code binary on Bernard's Mac (`versions/2.1.224`, 2026-08-07):

```
ANTHROPIC_BASE_URL          ANTHROPIC_AUTH_TOKEN       ANTHROPIC_CUSTOM_HEADERS
CLAUDE_CODE_USE_BEDROCK     ANTHROPIC_BEDROCK_BASE_URL CLAUDE_CODE_USE_VERTEX
```

So the shape is exactly the Bedrock analogy:

```
ANTHROPIC_BASE_URL=https://gate.bernarduriza.com \
ANTHROPIC_AUTH_TOKEN=<a per-consumer AIRE token> \
ANTHROPIC_CUSTOM_HEADERS='X-Aire-Project: aire-server' \
claude
```

`ANTHROPIC_CUSTOM_HEADERS` is what closes the one real gap: Claude Code has no
notion of `project_key`, so the routing key rides in a header the user sets.

## The one hard constraint — it must NOT go through the engine

The existing door (`POST /projects/{p}/sessions/{s}/messages`) is served by the
Agent SDK, which launches the Claude Code CLI as a subprocess. Serving
`/v1/messages` from that same engine would be:

    Claude Code → AIRE → Agent SDK → Claude Code (subprocess) → api.anthropic.com

The gateway door sits at a **lower level than the engine**: a streaming
pass-through proxy that never touches `engine/`. It forwards headers verbatim
(`anthropic-beta`, `cache_control` blocks, `anthropic-version`) and streams SSE
back byte-for-byte, or it silently breaks prompt caching and thinking blocks.
Buffering the body is not an option on a 512MB box — pass-through only.

## What it changes about the memory

This door sees a different granularity than the SDK door: raw API turns
(`messages[]` in, content blocks out), not an SDK session transcript. That is
not a defect — it is the level a gateway operates at — but it means a third
table (or a discriminated column), not a write into `claude_session_store`.
Every write is still an append, so [[write-only-daemon]] holds unchanged.

## Canonical path to reuse (Art. 6)

- The existing FastAPI + SSE + Bearer-auth shape in [`aire/server.py`](../../server/aire/server.py)
  and [`aire/messages.py`](../../server/aire/messages.py) — the new router is a
  sibling, not a rewrite.
- The mirror discipline already in [`aire/store.py`](../../server/aire/store.py) /
  [`aire/mirror.py`](../../server/aire/mirror.py) — uuid-dedup, eager append.
- Do NOT reinvent an LLM gateway (LiteLLM, Portkey, Helicone all exist). AIRE's
  reason to be its own is the mirror into the OWNER's Postgres; the proxy part
  is thin on purpose.

## The decision that's Bernard's

1. **Is the daemon allowed on the critical path of his own editor?** Every
   Claude Code turn would route through a $4/mo droplet in NYC. It is I/O, not
   compute, but a dead droplet means a dead editor. A local-first fallback
   (`unset ANTHROPIC_BASE_URL`) is one keystroke, but the failure mode is his to
   accept. See [[do-budget]].
2. **Per-consumer tokens.** The gateway needs a token per client that maps to a
   project key and (backlog #28) carries its own spend cap — a leaked editor
   token should not be able to burn the global budget.
3. **Whether the mirror stores the full request body**, prompts included. That
   is his codebase going into his own database — deliberate, but it should be a
   decision and not a side effect.

## Status / next step

Not built. Nothing blocks the design: the client half ships in the binary today
and the daemon already has the FastAPI/SSE/auth/mirror pieces. What's missing is
the router, the header→project mapping, and a decision on the three forks above.

Related: [[ssh-is-a-missing-endpoint]] (the formula that produced this item — a
need the API can't serve becomes a new endpoint), backlog #28 (per-token
budget), #29 (growing the SDK door).
