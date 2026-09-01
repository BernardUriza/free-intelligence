# 48 — Remote tools: the caller's own HTTP MCP

Status: In progress — AIRE's half shipped and verified at the door; the E2E waits on the consumer's endpoint
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

## What is still open — the other end of the data path

The persona-runner serves `/health` but **has no MCP endpoint** (`/mcp` → 404,
probed 2026-09-01). Until discord-bot ships its HTTP MCP server, no turn can
actually EXECUTE a remote tool — the feature is wired, refusal-proven, and
never once exercised end-to-end. Per [[both-ends-of-the-data-path]] this item
does not close on AIRE's half alone: Done means one real turn through the gate
whose agent calls `mcp__persona_memory__*` and gets a real result back from the
runner. That work lives in the discord-bot repo; this item tracks the receipt.
