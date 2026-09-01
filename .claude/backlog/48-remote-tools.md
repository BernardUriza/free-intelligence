# 48 — Remote tools: the caller's own HTTP MCP

Status: **Done 2026-08-28** — both halves live; the founding consumer's E2E receipt stands (see below; this file only learned it 2026-09-01)
Proposed: 2026-08-28 (shipped in `744ed51` + `adf3753` before this file existed — the index owed it for four days)

## What it is

A turn may carry `remote_tools: [{name, url, headers?}]` — HTTP MCP servers the
CALLER hosts, where the caller's own credentials live. The registry doctrine
stands: no command ever crosses the wire; the agent makes an outbound HTTPS
call. The wire names the url, the ENVIRONMENT defines the trust: the origin
must sit in `AIRE_REMOTE_TOOL_ORIGINS` or the turn is a 422 — which also closes
the SSRF an invited key would otherwise get.

Law and validation: [`engine/remote_tools.py`](../../server/aire/engine/remote_tools.py).
`RemoteTool` rides `TurnSpec`, so #38's rebind covers it; `__repr__` redacts
headers; no 422 can echo a header value (pinned by test).

## The founding consumer

discord-bot's `persona_memory`: the stage-2 migration left the persona with 2
of its 10 memory tools. This door is AIRE's half of restoring them without a
single Khimeras credential landing on the droplet. The allowlisted origin is
`https://persona-runner.greendune-53f1f4af.eastus2.azurecontainerapps.io`.

## Verified (2026-09-01, through the live gate, zero spend)

- Non-allowlisted origin → `422 origin https://attacker.example.com is not in
  AIRE_REMOTE_TOOL_ORIGINS`, refused before any dispatch.
- Allowlisted origin → passes `safe_remote_tools` (an empty-message probe with
  the persona-runner url fell through to the LATER `422 empty message` check,
  which only happens after the origin cleared).

Also fixed the same day: `AIRE_REMOTE_TOOL_ORIGINS` had been **hand-set on the
droplet** with no `~/.secrets/` home and no `compose_env` line — a kill test
would have silently disarmed the feature ([[device-verb-protocol]]'s exact
prohibition). Now `~/.secrets/aire-remote-tools.txt` + provisioning restore it.

## The other end of the data path — it was already alive, and this file said it wasn't

The first version of this file (2026-09-01, morning) claimed the persona-runner
*"has no MCP endpoint (`/mcp` → 404)"*. **False.** The endpoint is
`POST /mcp/{casita}` (`persona_runner/api/mcp_http.py`, deployed image
`2cdc203`), so the bare-`/mcp` probe hit a path with no route — and that
handler returns 404 *by design* on a missing or wrong bearer, so the probe
could not distinguish "not shipped" from "shipped, token elsewhere". A check
whose failure mode is indistinguishable from absence proves nothing
([[verify-before-assuming]] Rule 22); the corrected probe, same day, with the
real bearer (`~/.secrets/discord-bot-runner-mcp-token.txt`, provisioned on the
Container App as `RUNNER_MCP_TOKEN` + `RUNNER_MCP_BASE`):

    POST /mcp/probe-48 tools/list → 200, all 10 tools:
    get_user_facts, get_recent_messages, search_messages, get_disclosure_log,
    deep_memory, publish_html_artifact, get_emotional_arc, get_agent_facts,
    add_agent_fact, update_agent_fact

## The E2E receipt (the founding consumer's, 2026-08-28)

discord-bot's `.claude/backlog/aire-engine-stage2.md` finding 2, **CERRADO
2026-08-28** (v4.34.0/.1, receipt commit `e8e1e07`): Insult, running through
this door from the droplet, called `mcp__persona_memory__get_emotional_arc`
live in #general — the full chain (runner spec → fi-runner 0.21.0 →
`remote_tools` → droplet SDK → outbound HTTPS → `mcp_http` → Khimeras
Postgres) executed with a real result. Identity binds server-side from
`aire_turn_principals`, never from the model; `tools/call` outside a live turn
window answers "the turn window is closed" — by design, which is why the
freshest full-chain receipt belongs to a real persona turn, not to a probe.

What stays true from the morning's work: the origin allowlist fix
(`AIRE_REMOTE_TOOL_ORIGINS` now provisioned from `~/.secrets/`, `7321e55`) and
the two zero-spend door verifications (attacker origin 422; allowlisted origin
clears).
