# The gateway door — `POST /v1/messages`, so Claude Code points at AIRE

Status: Done (mechanism shipped 2026-08-07; the four forks below stay Bernard's)
Proposed: 2026-08-07 by Bernard ("¿algún día voy a poder usar Claude Code pero
que en vez de pegarle al endpoint de Anthropic le pegue a este? ¿como si fuera
un Bedrock?")

## What it is

A second door on the daemon: an endpoint that speaks the **Anthropic Messages
API wire format**, proxies each request straight to `api.anthropic.com`, and
mirrors both halves of the exchange into Postgres on the way through. Any client
that already knows how to talk to Anthropic — Claude Code first — points at AIRE
by env var and needs no other change.

**This is not a hypothesis.** Claude Code ships first-class support for exactly
this, with a published wire contract:

- [Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect)
- [Gateway protocol reference](https://code.claude.com/docs/en/llm-gateway-protocol) — the contract below
- LiteLLM, TrueFoundry and others already ship Anthropic-format gateways Claude
  Code drives in production, so the shape is proven by someone other than us.

```bash
ANTHROPIC_BASE_URL=https://gate.bernarduriza.com \
ANTHROPIC_AUTH_TOKEN=<a per-consumer AIRE token> \
claude
```

## The wire contract (verified against the protocol reference, 2026-08-07)

**Endpoints.** Only one is required:

| Path | Required? | Note |
|---|---|---|
| `POST /v1/messages` | **yes** | inference posts to `/v1/messages?beta=true` — match on the PATH, not the full URL |
| `POST /v1/messages/count_tokens` | optional | absent → Claude Code estimates context locally |
| `GET /v1/models?limit=1000` | optional | only for `/model` picker discovery; 3s timeout, **any redirect is treated as failure** (watch Caddy's http→https) |
| `HEAD /` | best-effort probe | may be rejected without breaking anything |

**Auth.** `ANTHROPIC_AUTH_TOKEN` → `Authorization: Bearer`; `ANTHROPIC_API_KEY`
→ `x-api-key`. The daemon should accept both.

**Forward unchanged, byte-for-byte:** `anthropic-version`, `anthropic-beta`
(comma-separated, **never allowlist individual values** — the set grows every
Claude Code release), and every `anthropic-*` request header and body field.
A gateway pinned to today's observed list breaks on the release that adds the
next capability. **Error response bodies too** — Claude Code pattern-matches the
upstream's error wording to auto-retry and disable a rejected capability; wrap
an error in our own envelope and the recovery path dies even with the right
status code.

**Streaming is mandatory and has a byte watchdog.** Responses must stream —
buffering a complete response before relaying stalls the client. Worse: on an
`ANTHROPIC_BASE_URL` connection Claude Code counts **every byte** the gateway
relays, including SSE `ping` events and comment lines, and **aborts a stream
that goes silent for 300 seconds**. Upstream pings are the only traffic during
long thinking pauses, so a proxy that swallows or batches them kills sessions
mid-thought. Pass-through, ping included, or nothing.

**The system-prompt attribution block.** Claude Code prepends an attribution
block as the FIRST entry of the `system` array. `api.anthropic.com` strips it
positionally — only if it arrives unchanged and first. Reordering the array,
prepending another block, or flattening it to a string defeats the strip: the
block then reaches the model AND the prompt-cache key. Forward `system` exactly
as received.

**WAF.** Claude Code prompts carry XML-style tags and source code, which match
cross-site-scripting body rules. Whatever sits in front (Caddy today) must not
inspect/rewrite the `/v1/messages` body — a short curl test passes while a real
session 403s.

## What Claude Code hands us for free (correcting the first draft of this item)

The first draft said we'd need `ANTHROPIC_CUSTOM_HEADERS` to carry a session
key. Half wrong — Claude Code **already sends its own attribution headers on
every request**, and the gateway may consume them without forwarding:

| Header | What it is |
|---|---|
| `x-claude-code-session-id` | unique id for the current Claude Code session — aggregate a whole session without parsing bodies |
| `x-claude-code-agent-id` | the subagent that issued the request (present only for spawned agents) |
| `x-claude-code-parent-agent-id` | the agent that spawned it, for nested agents |

So the mirror's session key arrives for free, and **subagent traffic is
attributable** — the parallel-agent tree reconstructs from headers alone.
`ANTHROPIC_CUSTOM_HEADERS` (documented for exactly "a tenant identifier or a
routing key") is still how a `project_key` would ride:

```bash
ANTHROPIC_CUSTOM_HEADERS='X-Aire-Project: aire-server'
```

Note these IDs identify an agent, not a person — don't treat them as identity.

## The hard constraint — it must NOT go through the engine

The existing door (`POST /projects/{p}/sessions/{s}/messages`) is served by the
Agent SDK, which **spawns the Claude Code CLI as a subprocess**. Verified in the
installed SDK, not assumed:

- `subprocess_cli.py:89` — `shutil.which("claude")`
- `subprocess_cli.py:225` — `cmd = [self._cli_path, "--output-format", "stream-json", …]`
- `subprocess_cli.py:474` — `anyio.open_process(cmd, …, env=process_env)`
- `subprocess_cli.py:431` — `process_env = {**inherited_env, …}` where
  `inherited_env` is **`os.environ`** minus `CLAUDECODE`

Anthropic's own docs confirm the design: *"The Agent SDK has no gateway-specific
options; it passes environment variables to the Claude Code process it spawns…
Python: `ClaudeAgentOptions(env=…)` merges on top of the inherited environment."*

Two consequences, and the second is a live footgun:

1. Serving `/v1/messages` from the engine would recurse:
   `Claude Code → AIRE → Agent SDK → claude (subprocess) → api.anthropic.com`.
   The gateway door sits **below** the engine — a streaming proxy that never
   touches `engine/`.
2. **The day `ANTHROPIC_BASE_URL` lands in `/etc/aire/env`, every CLI the engine
   spawns inherits it and calls the daemon back — an infinite loop inside the
   droplet.** The engine must scrub `ANTHROPIC_BASE_URL` (and
   `ANTHROPIC_AUTH_TOKEN`) from the child env via `ClaudeAgentOptions.env`, or
   the gateway must never be configured process-wide on the box.
   Checked 2026-08-07: neither var appears anywhere in `server/` today, so the
   trap is future, not present.

## What it changes about the memory

This door sees a different granularity than the SDK door: raw API turns
(`messages[]` in, content blocks out) keyed by `x-claude-code-session-id`, not
an SDK session transcript. That is the level a gateway operates at — it means a
third table (or a discriminated column), not a write into
`claude_session_store`. Every write is still an append, so
[[write-only-daemon]] holds unchanged.

## The price Bernard pays (each verified in the docs, none is a guess)

1. **Voice dictation stops working.** It reaches a claude.ai transcription
   endpoint and is unavailable while `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY`
   / an `apiKeyHelper` is active. Bernard dictates — this is the sharpest cost.
2. **Remote Control stops working.** Since Claude Code v2.1.196 it is disabled
   whenever `ANTHROPIC_BASE_URL` points at a non-Anthropic host; a claude.ai
   login is not enough to restore it.
3. **Fast mode reports unavailable.** Its availability check goes straight to
   `api.anthropic.com` and ignores the base URL; authenticated with only a
   bearer token, Claude Code treats fast mode as disabled without even sending
   the check. Recoverable with `CLAUDE_CODE_SKIP_FAST_MODE_ORG_CHECK=1`.
4. Minor: the WebFetch domain-safety preflight still calls `api.anthropic.com`
   (`skipWebFetchPreflight: true` to silence); an auth-conflict warning appears
   while a claude.ai login is also saved (`/logout` clears it).

All four are per-shell — `unset ANTHROPIC_BASE_URL` and the editor is back on
first-party — so the practical shape is **opt-in per session, not machine-wide**.

## Canonical path to reuse (Art. 6)

- The FastAPI + SSE + Bearer-auth shape already in
  [`aire/server.py`](../../server/aire/server.py) and
  [`aire/messages.py`](../../server/aire/messages.py) — the new router is a
  sibling, not a rewrite.
- The append discipline in [`aire/store.py`](../../server/aire/store.py) /
  [`aire/mirror.py`](../../server/aire/mirror.py) — uuid-dedup, eager append.
- Do NOT reinvent an LLM gateway (LiteLLM, Portkey, Helicone all ship one).
  AIRE's reason to be its own is the mirror into the OWNER's Postgres; the proxy
  half is thin on purpose.

## The decision that's Bernard's

1. **Is the daemon allowed on the critical path of his own editor?** Every turn
   routes through a $4/mo droplet in NYC; a dead droplet is a dead editor. The
   escape is one `unset`, but the failure mode is his to accept ([[do-budget]]).
2. **Are the three dead features acceptable** (dictation, Remote Control, fast
   mode) — and is per-session opt-in the right default rather than a global
   `settings.json`?
3. **Per-consumer tokens** mapping to a project key, each with its own spend cap
   (backlog #28) — a leaked editor token must not burn the global budget.
4. **Does the mirror store full request bodies, prompts included?** That is his
   codebase entering his own database — deliberate, not a side effect.

## Status / next step

**Shipped 2026-08-07.** What landed:

- `server/aire/gateway.py` — the router: `POST /v1/messages` (query forwarded,
  path matched), `POST /v1/messages/count_tokens`, `GET /v1/models`. Streaming
  byte-for-byte pass-through (httpx, `aiter_raw`), pings and SSE comments
  included; errors relayed unwrapped; auth pass-through (upstream judges the
  credential — the `/v1/` prefix is exempt from AIRE's own Bearer door).
  Upstream override for tests: `AIRE_GATEWAY_UPSTREAM`.
- `server/aire/gateway_mirror.py` + `gateway_assemble.py` — the NEW append-only
  `aire_gateway_log` table (created lazily as role `aire`, so the reader's
  default-privileges grant covers it): one `request` row before the relay, one
  `response` row when the stream ends (deltas assembled server-side into the
  final message + stop_reason + usage). Mirror failures never fail the relay.
- The recursion scrub in `engine/options.py` — every spawned CLI gets
  `ANTHROPIC_BASE_URL` pinned to `https://api.anthropic.com` and
  `ANTHROPIC_AUTH_TOKEN` blanked, so a gateway var in `/etc/aire/env` can never
  loop the engine back into the daemon.
- Tests: `server/tests/test_gateway.py` — real-socket relay (incremental, not
  buffered), header forwarding, unwrapped errors, and both mirror rows, against
  a fake upstream with delays.

Still open (the forks above, all Bernard's): whether his editor actually rides
through the droplet, per-consumer tokens with budgets (#28), and the
header→project mapping beyond the `X-Aire-Project` column already mirrored.

Related: [[ssh-is-a-missing-endpoint]] (the formula that produced this item),
backlog #28 (per-token budget), #29 (growing the SDK door).
