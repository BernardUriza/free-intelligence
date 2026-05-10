# Testing Rules

## Verify Live Infra State Before Asserting — MANDATORY

Before making any claim about how production infrastructure is configured — ingress
exposure, env vars, secrets, blob state, deploy revision, container image tag,
network policy, anything — run the live query first. `CLAUDE.md` and the files
under `.claude/rules/` describe **intended** state at the moment they were written
and rot silently as the user changes infra without updating the docs.

**Do not** quote a doc as if it were current truth. **Do** run one read-only
command and quote the actual output.

| Question                              | Verify with                                                                                          |
|---------------------------------------|------------------------------------------------------------------------------------------------------|
| Is the debug endpoint exposed?        | `az containerapp show --name insult-bot --resource-group insult-rg --query properties.configuration.ingress` |
| What env vars / secrets does prod have? | `az containerapp show --name insult-bot -g insult-rg --query "properties.template.containers[0].env"` |
| What is the current deployed revision? | `az containerapp show ... --query properties.latestRevisionName`                                     |
| What is in the backup blob right now? | `az storage blob show --account-name insultstorage --container-name insult-bot --name memory.db --query "{modified:properties.lastModified, size:properties.contentLength}"` |
| What is the local file actually doing? | `Read` it. Do not paraphrase from memory.                                                            |
| Is CI green / a PR merged?            | `gh run list`, `gh pr view`                                                                          |

**Why this rule exists:** in an experimental production environment, the user
changes infra faster than the docs. Asserting a stale claim once costs minutes;
asserting it twice in the same session burns the user's trust and an hour of
their day. A 30-second read-only command is always cheaper than a wrong claim.

**If a doc and live state disagree, trust live state and update the doc** in the
same turn (or flag the divergence). Never let a known-stale claim sit unfixed
once you have observed the truth.

This rule is the precondition to the diagnostic workflow further down (KQL first,
debug endpoint for content). Diagnostic queries themselves are useless if you
have already lied about how the system is wired.

## Pre-Push Verification — MANDATORY

Before EVERY push, verify that code actually works at the Python import level, not just at the lint/test level:

1. **SDK class existence**: If you reference a new exception class, enum, or attribute from an external SDK (e.g., `anthropic.OverloadedError`), ALWAYS verify it exists first:
   ```bash
   python3 -c "import anthropic; print(hasattr(anthropic, 'OverloadedError'))"
   ```
   `ruff check` and `pytest` may pass even when the class doesn't exist (if the import is inside a try/except or conditional path). Only a live import test catches this.

2. **Real import smoke test**: After adding imports from external packages, verify the module loads:
   ```bash
   python3 -c "from insult.core.llm import LLMClient; print('OK')"
   ```

3. **Never assume SDK APIs exist**: Always check `dir(module)` or `hasattr(module, 'ClassName')` before using a class you haven't used before in this codebase.

4. **If CI fails, don't just re-push with a guess**: Read the CI error, reproduce it locally, then fix with verification.

## Browser Testing
- Always test the bot's web-facing features using Chrome DevTools (via MCP chrome-devtools)
- Use DevTools to verify Discord interactions when possible: navigate to Discord web, inspect network requests, check console for errors
- Prefer automated browser verification over manual "go check it" instructions

## Debug HTTP Endpoint (read-only introspection)

The bot exposes a read-only HTTP server (`insult/core/debug_server.py`) that Claude Code can hit directly to inspect state without needing the Discord MCP server.

### Setup
- Requires `DEBUG_TOKEN` in `.env` — fail-closed if unset (server does NOT start)
- Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- Defaults: `DEBUG_HOST=0.0.0.0`, `DEBUG_PORT=8787`
- Auth: `Authorization: Bearer <token>` header on every endpoint except `/debug/health`

### Endpoints
| Method | Path | Query params | Returns |
|--------|------|--------------|---------|
| GET | `/debug/health` | — | `{"status": "ok"}` (no auth) |
| GET | `/debug/messages` | `channel_id` (req), `limit` (1-500, default 15) | Last N messages for channel |
| GET | `/debug/channels` | `guild_id` (req), `since_hours` (default 24) | Channel activity counts |
| GET | `/debug/stats` | — | Total messages / users / channels |

### How to use from Claude Code
```bash
# Load token from .env
TOKEN=$(grep DEBUG_TOKEN .env | cut -d= -f2)

# Read last 15 messages in a channel
curl -s "http://localhost:8787/debug/messages?channel_id=123456&limit=15" \
  -H "Authorization: Bearer $TOKEN" | jq .

# List active channels in a guild in last 24h
curl -s "http://localhost:8787/debug/channels?guild_id=99999&since_hours=24" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Notes
- Read-only — no write paths
- In Azure Container Apps: **publicly reachable** at `https://insult-bot.nicecliff-10074f57.eastus.azurecontainerapps.io` (external ingress targets port 8787). Bearer token from Azure secret `debug-token` is the only protection — verify with `az containerapp show -n insult-bot -g insult-rg --query properties.configuration.ingress` before claiming otherwise
- Uses `hmac.compare_digest` for timing-safe token comparison
- For local testing, bot must be running (`python -m insult run`)

### MANDATORY diagnostic workflow

A complete diagnosis in this app is, in order:

1. **Azure Log Analytics by time range — ALWAYS first.** Pull every event the
   bot emitted during the window where the user reports misbehavior. Use the
   KQL REST path documented in `memory/reference_azure_log_analytics.md`
   (workspace customer ID `a07bf4c8-22ff-455a-b7bd-91055da53b28`, table
   `ContainerAppConsoleLogs_CL`, filter `ContainerAppName_s == "insult-bot"`).
   Every structured signal lives here: `preset_classified`, `flow_pressure`,
   `flow_expression`, `llm_request`, `llm_response` (input/output tokens,
   cache hits, stop_reason), `llm_timeout`, `llm_failed`, `llm_bad_request`,
   `tool_calls_detected`, `character_break_detected`, `chat_turn_end`, etc.
   This reconstructs 90%+ of any incident without ever reading message text.

2. **Debug endpoint ONLY when log signals are insufficient.** If after
   reading KQL you still need the literal user/bot text to corroborate a
   hypothesis (e.g. you see `preset=default_abrasive modifiers=[memory_recall]`
   and `output_tokens=22` but cannot tell whether the 22-token reply was
   appropriate without seeing what the user asked), THEN hit
   `/debug/messages?channel_id=<id>&limit=30`. The endpoint is LOCAL-ONLY
   (Azure Container App has no ingress), so it only works while running
   the bot on this Mac — it is a corroboration tool, not the first move.

Rationale: starting with the endpoint before KQL forces the user to paste
channel IDs and wait for a local bot; starting with narration about what
you cannot see burns their trust. Start with `TimeGenerated` + structured
events. Ask for channel text only when the structured data does not answer
the question.

This replaces the prior "debug endpoint first" rule. That rule was written
while Log Analytics was not yet proven reachable from this Mac — once the
REST path was validated (2026-04-24) the ordering flipped: KQL first,
endpoint for content verification.

### Detect dropped messages — MANDATORY before claiming "no activity"

When `total_messages` is flat or the user reports "the bot died", DO NOT
conclude "nobody wrote to it" until you have proven there are no
**silently swallowed messages**. The bot can be alive at the gateway
(heartbeats green, `guilds: 1`) and still drop inbound messages mid-pipeline
(attachment processing, LLM call, post-LLM mutation, delivery). Those
deaths leave a `chat_turn_start` with no paired `chat_turn_end`, OR
no `chat_turn_start` at all if the drop is at the cog/listener level.

**Three signals that scream "swallowed message" — check them in order:**

1. **Consecutive user messages with no bot reply between them.** Pull the
   last 30+ messages from `/debug/messages` (NOT 15 or 20 — too short to see
   the pattern). If the same `author_id` sends 3+ messages within a short
   window with no bot message interleaved, one was eaten. Common shape:
   long message + image → "como ves" → "ups" → "okok" — the user is
   poking a corpse.

2. **`chat_turn_start` without paired `chat_turn_end` (same `request_id`).**
   ```kql
   ContainerAppConsoleLogs_CL
   | where ContainerAppName_s == "insult-bot" and TimeGenerated > ago(24h)
   | extend req = tostring(parse_json(Log_s).request_id),
            ev  = tostring(parse_json(Log_s).event)
   | where ev in ("chat_turn_start", "chat_turn_end")
   | summarize starts = countif(ev == "chat_turn_start"),
               ends   = countif(ev == "chat_turn_end") by req
   | where starts > ends
   ```
   Every orphan `request_id` is a message that entered the pipeline and
   never came out. Cross-reference with `stage_attachments_processed`,
   `stage_facts_loaded`, `llm_call_start`, `llm_call_complete` to find
   the stage where it died.

3. **`unanswered` field in `proactive_message_sent`.** The proactive system
   itself counts how many user messages went without a reply
   (`unanswered: 3` means the bot already noticed it ate three). Treat
   any `unanswered >= 2` in a recent proactive event as a self-report of
   the bug — the bot is literally asking you to check why.

**Why this rule exists:** on 2026-05-09 a user reported "se murió otra vez"
and the assistant pulled only 20 messages from `/debug/messages`, saw the
last one was "Okok", and concluded "nobody has written for 31h". The
real story was visible in those same 20 messages: four consecutive user
messages from the same author (one with an image attachment) with zero
bot replies between them. The user's "Ups / Okok" was acknowledging the
silence, not closing the conversation. The smoking gun was also visible
in `proactive_message_sent ... unanswered: 3` from earlier the same day —
the bot had counted the swallowed messages and the assistant didn't read
the field. Pulling 20 messages is too few; reading them without checking
author-sequence is worse than reading none.

**Apply this rule any time:** the user reports degraded responsiveness,
`total_messages` is unchanging across two heartbeat windows, or you see
a `proactive_message_sent` with `unanswered > 0`. Pull `limit=50` minimum
from `/debug/messages`, group by `author_id`, and flag any consecutive
run of 2+ user messages without an interleaved bot message.

### Resilience anti-patterns — DO NOT introduce

These are codified after the 2026-05-08 outage post-mortem (full ADR
in `.claude/plans/turn_resilience.md`). Every entry is a real failure
mode that bit us or that production-product post-mortems documented.

1. **`async with channel.typing(): await llm_or_other_long_call(...)`** —
   `Typing.__aenter__` makes a blocking `send_typing` HTTP request
   *before* the body runs. If the channel is hot, a 40062
   (`ServiceResourceIsBeingRateLimited`) here kills the entire turn
   even though the LLM never ran. Fix: typing is a fire-and-forget
   background task that wraps its own `HTTPException`. Reference:
   [discord.py context_managers.py:54-92](https://github.com/Rapptz/discord.py/blob/master/discord/context_managers.py).

2. **`except Exception: log + send(error_message)` without an inner
   try/except on the `send`** — when the exception was caused by the
   channel being rate-limited, the in-character error message also
   429s and the user sees nothing. Always wrap the recovery `send`
   with its own guard, and fall through to `message.add_reaction(...)`
   (different bucket, almost always survives) on secondary failure.

3. **Stateless triviality filter for life-checks** — discarding
   "ups"/"okok"/"hola?" with no awareness of whether the previous
   turn failed is how the bot becomes invisible to a user trying to
   wake it. The trivial gate must consult `ChannelHealth.last_outcome`
   and bypass the skip when the previous turn failed within 60 s.

4. **Logging an event whose name lies about which stage failed** —
   `chat_llm_failed` MUST NOT fire when the LLM never ran (e.g., when
   `channel.typing()` exploded before the LLM call). Failure stage is
   a typed field on `chat_turn_end`, not buried in the event name.

5. **Ignoring `retry-after` from the upstream** — Anthropic returns
   `retry-after` in 429/529. Vercel AI SDK
   [#7247](https://github.com/vercel/ai/issues/7247) is the canonical
   anti-pattern (their retries collide on the worst possible second).
   Always honor the header when ≤ 60 s before falling through to
   jittered backoff.

6. **Out-of-character degradation text in user-facing error paths** —
   `persona.md` forbids exposing model identity. ChatGPT and Cursor
   send "model overloaded" text; we cannot. Use either a reaction
   (`[REACT:⏳]`) or an in-character `core/errors.py` message that
   does not name the underlying tech.

7. **Per-upstream circuit breaker for a single-upstream client** —
   Marc Brooker (AWS, author of the canonical jitter paper) explicitly
   advises against this in his [2022
   post](https://brooker.co.za/blog/2022/02/16/circuit-breakers.html):
   *"Circuit breakers are designed to turn partial failures into
   complete failures."* For Anthropic API (single upstream), opening
   the breaker just means "the bot is dead" — a worse failure than
   a per-request retry+jitter. Use token bucket / retry budget instead.
   Per-Discord-channel breakers are fine because channels ARE sharded.

8. **Pure exponential backoff (no jitter)** — `wait = 2 ** attempt`
   produces retry storms ("thundering herd"). AWS Standard SDK uses
   Full Jitter (`random.uniform(0, min(2 ** attempt, cap))`). Apply
   it to every retry path.

9. **`asyncio.gather` over many channels without a per-channel
   semaphore** — guaranteed Discord 429 storm. Documented in
   [discord.py #5806](https://github.com/Rapptz/discord.py/issues/5806).

10. **`time.sleep()` (sync) inside `async with channel.typing()`** —
    blocks the event loop, the typing keepalive cannot refresh, dies
    at 10 s. Documented in
    [discord.py discussion #5969](https://github.com/Rapptz/discord.py/discussions/5969).

11. **Health probe that calls downstream dependencies** — couples
    your pod's restart decision to *their* health. A 30 s downstream
    blip kills your pod and amplifies the outage. Liveness = "is
    *this* process healthy"; readiness is the right place for
    dependency checks (Kubernetes guidance).

12. **Adopting an abandoned library because a previous round of
    research recommended it** — verify lib health LIVE before
    adopting. `purgatory` was recommended by an earlier research pass
    and turned out to be 2 stars / 3 unresponded Snyk issues / no
    real production users. Always run
    `gh api repos/<owner>/<lib>` (stars, last commit, open issues)
    and `gh search code 'from <lib> import'` (real dependents)
    before adding to `pyproject.toml`.

13. **Trusting a Discord error code from memory without verifying** —
    40060 is `InteractionHasAlreadyBeenAcknowledged` (slash commands),
    NOT a rate limit. 40062 is `ServiceResourceIsBeingRateLimited`.
    They are unrelated. Always verify against
    [discord-api-types RESTJSONErrorCodes](https://discord-api-types.dev/api/discord-api-types-v10/enum/RESTJSONErrorCodes)
    before quoting an error code as fact.

## E2E Testing with Discord MCP
When you need to verify that the bot actually works end-to-end (not just unit tests), use the Discord MCP server to interact with a real Discord server. This Mac is the server.

### Setup
- The MCP server `barryyip0625/mcp-discord` (or `SaseQ/discord-mcp`) provides tools like `discord_send`, `discord_read_messages`, `discord_search_messages`
- The bot must be running locally on this Mac before E2E tests
- Use a dedicated testing Discord server/channel (not production)
- The bot's `DISCORD_TOKEN` from `.env` is the same token the MCP uses

### How to Run E2E Tests
1. Start the bot locally: `python -m insult run`
2. Use MCP Discord tools to send a command: `discord_send` with `!chat <test message>`
3. Wait briefly, then `discord_read_messages` to read the bot's response
4. Verify the response: no character breaks, correct language, in-character tone
5. Use `discord_search_messages` to verify memory persistence across messages

### E2E Test Mode (App-Level Bypass)
- The app should support a `E2E_TEST_MODE=true` environment variable
- When enabled: reduces cooldowns to 0, disables rate limiting, enables a `!e2e_reset` command to clear test data
- This mode should ONLY be active while the bot is running locally for testing — never in production
- The bypass is controlled via `.env`, not hardcoded

### When to Run E2E Tests
- After implementing new commands or changing chat flow
- After modifying persona.md or character break detection
- After changing memory/context building logic
- When unit tests pass but you want to verify the full integration
- Do this naturally — don't wait for the user to ask. If you changed bot behavior, verify it works

### E2E Test Checklist
- [ ] Bot responds to `!chat` in the correct language
- [ ] Bot stays in character (no "I'm an AI", no "Claude", no apologies)
- [ ] Bot remembers context from previous messages in the same channel
- [ ] Error responses are in-character (not exposing internals)
- [ ] `!perfil` shows style profile after 5+ messages
- [ ] Long messages are chunked correctly (< 2000 chars per message)

## E2E via CI/CD Pipeline (Production Verification)

E2E testing means pushing code, triggering the full CI/CD pipeline, and monitoring the deployment to Azure. This is the real verification flow:

### Steps
1. Commit and push to `main`
2. CI runs (GitHub Actions: lint, tests, audit, security) — monitor with `gh run watch --exit-status`
3. On CI success, CD triggers automatically (workflow_run on CI completion)
4. CD builds Docker image, pushes to Azure Container Registry (insultacr), deploys to Azure Container Apps (insult-bot in insult-rg)
5. Monitor CD deployment via `az` CLI:
   - `gh run list --workflow=cd.yml --limit=3` to check CD run status
   - `az containerapp show --name insult-bot --resource-group insult-rg --query "properties.latestRevisionName"` to verify new revision
   - `az containerapp logs show --name insult-bot --resource-group insult-rg --follow` to tail logs and confirm bot starts healthy
6. Once deployed, verify the bot responds in Discord (either manually or via MCP)

### Key Resources
- **ACR**: insultacr.azurecr.io
- **Container App**: insult-bot (resource group: insult-rg)
- **CD workflow**: `.github/workflows/cd.yml` — triggers on CI success on main
