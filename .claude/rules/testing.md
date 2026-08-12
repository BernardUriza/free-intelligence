# Testing Rules

> **Name disclaimer (post-purga 2026-07-14, commit 2f8d9ad + host cutover
> 2026-07-15)**: the live Container Apps are **`persona-gateway`** (the Discord
> turn path, all personas), **`persona-runner`** (shared Claude-Agent-SDK brain)
> and **`khimeras-host`** (demux reception host). The legacy **`discord-bot`**
> plumbing app is RETIRED — scaled to zero, dead FQDN; `alice-bot` no longer
> exists as a Container App. Older `insult-bot` / `discord-bot` references in
> KQL filters and `az` snippets in memory files describe historical state —
> for live infra always filter/query the three live app names.

## Verify Live Infra State Before Asserting — MANDATORY

Before making any claim about how production infrastructure is configured — ingress
exposure, env vars, secrets, deploy revision, container image tag,
network policy, anything — run the live query first. `CLAUDE.md` and the files
under `.claude/rules/` describe **intended** state at the moment they were written
and rot silently as the user changes infra without updating the docs.

**Do not** quote a doc as if it were current truth. **Do** run one read-only
command and quote the actual output.

| Question                              | Verify with                                                                                          |
|---------------------------------------|------------------------------------------------------------------------------------------------------|
| What Container Apps are live / scaled? | `az containerapp list -g insult-rg --query "[].{name:name, running:properties.runningStatus, replicas:properties.template.scale.minReplicas}" -o table` |
| What env vars / secrets does prod have? | `az containerapp show --name persona-gateway -g insult-rg --query "properties.template.containers[0].env"` |
| What is the current deployed revision? | `az containerapp show --name persona-runner -g insult-rg --query properties.latestRevisionName`      |
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
DB read for content). Diagnostic queries themselves are useless if you
have already lied about how the system is wired.

## Pre-Push Verification — MANDATORY

Before EVERY push, verify that code actually works at the Python import level, not just at the lint/test level:

1. **SDK class existence**: If you reference a new exception class, enum, or attribute from an external SDK (e.g., `anthropic.OverloadedError`), ALWAYS verify it exists first:
   ```bash
   conda run -n discord-bot python -c "import anthropic; print(hasattr(anthropic, 'OverloadedError'))"
   ```
   `ruff check` and `pytest` may pass even when the class doesn't exist (if the import is inside a try/except or conditional path). Only a live import test catches this.

2. **Real import smoke test**: After adding imports from external packages, verify the module loads:
   ```bash
   conda run -n discord-bot python -c "from khimeras_shared.guidance import guidance_for_turn; print('OK')"
   ```

3. **Never assume SDK APIs exist**: Always check `dir(module)` or `hasattr(module, 'ClassName')` before using a class you haven't used before in this codebase.

4. **If CI fails, don't just re-push with a guess**: Read the CI error, reproduce it locally, then fix with verification.

## Browser Testing
- Always test the bot's web-facing features using Chrome DevTools (via MCP chrome-devtools)
- Use DevTools to verify Discord interactions when possible: navigate to Discord web, inspect network requests, check console for errors
- Prefer automated browser verification over manual "go check it" instructions

## Introspection surfaces (post-purga)

> **Historical note:** the old read-only debug HTTP server
> (`insult/core/debug_server.py`, `/debug/messages` on port 8787) **died with
> `personas/` in 2f8d9ad** — `grep -rn "8787\|debug/messages" --include='*.py' .`
> returns nothing live. Do not curl those endpoints; do not tell Bernard they
> exist. The `persona-gateway` binds port 8788 for its own `/invite` + health
> API (`persona_gateway/invite_server.py`), which is NOT a message-introspection
> surface.

The live introspection surfaces are:

1. **Azure Log Analytics (KQL)** — structured events from the three live apps
   (`ContainerAppName_s in ("persona-gateway", "persona-runner", "khimeras-host")`),
   table `ContainerAppConsoleLogs_CL`, workspace in
   `memory/reference_azure_log_analytics.md`.
2. **The Postgres data plane directly** — messages/facts live in Azure
   PostgreSQL (`POSTGRES_URL`, schema in
   `khimeras_shared/memory/postgres_schema.sql`). A read-only `psql` query is
   the modern replacement for every old `/debug/messages` step.
3. **Discord itself via the debug Chrome (`:9333`)** — the canonical history of
   what was actually said and answered.

### MANDATORY diagnostic workflow

A complete diagnosis in this app is, in order:

1. **Azure Log Analytics by time range — ALWAYS first.** Pull every event the
   system emitted during the window where the user reports misbehavior. Use the
   KQL REST path documented in `memory/reference_azure_log_analytics.md`
   (table `ContainerAppConsoleLogs_CL`, filter on the live app names above).
   This reconstructs 90%+ of any incident without ever reading message text.

2. **Direct DB read ONLY when log signals are insufficient.** If after
   reading KQL you still need the literal user/bot text to corroborate a
   hypothesis, query Postgres directly (read-only) or read the channel in
   Discord web. Content reads are a corroboration tool, not the first move.

Rationale: starting with content before KQL forces the user to paste
channel IDs and wait; starting with narration about what
you cannot see burns their trust. Start with `TimeGenerated` + structured
events. Go to channel text only when the structured data does not answer
the question.

### Detect dropped messages — MANDATORY before claiming "no activity"

When the user reports "the bot died", DO NOT conclude "nobody wrote to it"
until you have proven there are no **silently swallowed messages**. The
gateway can be alive at the Discord gateway (heartbeats green) and still drop
inbound messages mid-pipeline (attachment processing, the runner call, marker
parsing, delivery). Signals to check, in order:

1. **Consecutive user messages with no bot reply between them.** Pull the last
   30+ rows for the channel from Postgres (or scroll Discord web itself). If
   the same author sends 3+ messages within a short window with no bot message
   interleaved, one was eaten. Common shape: long message + image → "como
   ves" → "ups" → "okok" — the user is poking a corpse.
2. **A turn-start log event without its paired turn-end** (same request id) in
   KQL — every orphan is a message that entered the pipeline and never came
   out. Cross-reference the stage events around it to find where it died.
   Gateway-side failures log `persona_gateway_turn_failed`.

**Why this rule exists (historical, 2026-05-09 — the module it names died in
2f8d9ad; the lesson is alive):** a user reported "se murió otra vez" and the
assistant pulled only 20 messages from the then-live `/debug/messages`
endpoint, saw the last one was "Okok", and concluded "nobody has written for
31h". The real story was visible in those same 20 messages: four consecutive
user messages from the same author (one with an image attachment) with zero
bot replies between them. The user's "Ups / Okok" was acknowledging the
silence, not closing the conversation. Pulling 20 messages is too few; reading
them without checking author-sequence is worse than reading none.

**Apply this rule any time** the user reports degraded responsiveness. Pull 50+
rows minimum, group by author, and flag any consecutive run of 2+ user
messages without an interleaved bot message.

### Inspect the database BEFORE believing the chat — MANDATORY

When a user reports "the bot doesn't remember X", "forgot facts Y",
"loses context Z", or any other complaint about memory, your **first
move** is to query the database directly. NOT the chat history. NOT
the user's testimony about what was said. NOT the LLM's narration of
what it has in context. The database (Azure Postgres via `POSTGRES_URL`).

**Concrete debugging order when "the bot forgot something":**

1. **Query Postgres** and verify the message in question is physically
   present. If it is NOT in the DB, the model is telling the truth that it
   doesn't have it — the storage layer dropped it. Stop blaming the model.
2. **Query KQL** for the turn's store/turn-end events at that message's
   timestamp. If the events fire but the row is absent, the bug is between
   the log line and the actual INSERT.
3. **Compare DB rows against Discord's own history.** Discord itself is the
   canonical source — diff against what the DB has.
4. **Only after all three of the above** is it worth investigating
   prompt construction, context truncation, attention dilution,
   model behavior. Those are all downstream of the data plane.

**Anti-pattern: chat-driven debugging.** Believing the user's
narration ("I pasted the CV twice and the bot says it doesn't have
it"), then iterating on prompt fixes, formatting tweaks, classifier
changes, persona tweaks — without ever reading the DB. The user is
reporting a symptom; the DB tells you whether the data even exists.
Skipping that step is what a chat product would do, not what a
developer would do.

**Why this rule exists (historical, 2026-05-12 — pre-Postgres, when the data
plane was SQLite-in-container with a blob-restore race):** the assistant spent
~3 hours iterating fixes (preset routing, formatting normalization,
top-N fact retrieval, timestamp prefix removal) for a "memory bug"
that was actually a deploy-induced storage drop. A 30-second DB query
at minute 1 would have shown the messages were physically absent
and immediately pointed at the blob-restore race, saving ~3 hours of
misdiagnosed work and the user's trust. The user's exact words were
*"simplemente es lo que hace un dev normalmente — observar la base de
datos"* — and they were right. (The blob race itself was killed by the
Postgres migration, 2026-05-13; the verify-the-data-plane-first lesson is
permanent.)

**Applies to ALL "memory" or "forgot" or "lost context" reports**,
regardless of how persuasive the user's narrative or how confident
the model's "I don't have that in this session". The DB is the
arbiter, not the model and not the user.

#### Sub-rule: NO speculative explanation before verification

The above rule says "check the DB". This sub-rule is stricter:
**before producing any explanation of why the bot behaved a certain
way, run the verification queries first.** Not "after I share a
hypothesis." Not "if the user asks for details." Not "later when I
have time." First. Always.

Anti-pattern to refuse: the user pastes a few turns of bot output
and asks "why did this happen?". The right move is:

1. DB query → is the relevant data in the DB?
2. KQL for that turn's classification + context events → what did the bot
   actually receive?
3. Only after (1) and (2): write the explanation.

If you find yourself typing "the model is probably doing X because
Y" without having run either query, **stop and run them**. Whatever
you were about to write is fiction until proven. Even plausible
fiction (matching what real LLMs sometimes do) is wrong here, because
fiction that sounds right is harder to disbelieve than fiction that
sounds wrong, and the user trusts you to distinguish.

This sub-rule was added on 2026-05-12 after the assistant violated
the parent rule within 30 minutes of writing it. Bernard pasted two
bot turns where Insult said *"No lo tengo. Nunca llegó a esta
sesión"* about Alex's CV right after a recovery had restored the
CV to the DB. The assistant wrote a confident multi-paragraph
explanation ("the model is consistency-locked on its own prior
disclaimers in the thread") — without checking the DB
to confirm the CV was actually there, without checking KQL to
see what the classifier had chosen. Bernard caught it immediately.
The explanation might have been partly right; the violation is
offering it before checking.

The verification cost in that case was ~30 seconds (one query + one
KQL). The cost of speculating wrong is the user's trust, which by
that point in the day was already on its last reserve. Pay the 30
seconds. Always.

#### Sub-sub-rule: a partial verification does NOT license expansion

The rule above says "verify before explaining". This is the stricter
form: **even after verifying ONE thing, a hypothesis built on top of
that one verification is still speculation about the next thing.**
Partial data does not authorize full narrative.

Concrete example from 2026-05-12, same day, ~20 minutes after the
parent rule was written:

1. Bernard reports memory bug. Assistant explains "the model has
   the data, it's ignoring context." Bernard catches: no DB check.
   Rule added.
2. Assistant verifies via SQL that the CV is in the DB. ✓
3. Assistant then asserts (without further verification): "the
   recent window excludes the CV because there are >50 messages
   after it, therefore the model doesn't have it in context, so
   the bot is being honest". This narrative is built on top of one
   verified fact (CV is in DB at older timestamps) BUT extends to
   multiple unverified claims:
   - that the recent-window read is the only mechanism putting messages in
     context (false — the keyword-relevant search also pulls
     older messages)
   - that the Other People block's facts don't include CV-detail
     facts (verified — they're general summaries)
   - that the model "is being honest" rather than the alternative
     interpretation that the relevant search ran and the model
     ignored its results

   The first claim was never checked. The third is a narrative
   choice, not a verification.

The user called it out: *"sigues inventando narrativas sin
verificar y tus narrativas me convencen es lo peor"*. The danger
isn't bad narratives — it's narratives that PASS the plausibility
filter without passing the truth filter. The reader's trust does
the rest.

**Operational form of this sub-rule:** every clause in an
explanation that asserts a causal relationship ("therefore",
"because", "so the model is X", "the bug is Y") must point to a
specific command output already shown in the same response. If a
clause has no anchor, it is speculation regardless of how
plausible it sounds. Stop the sentence. Run the check. Then write.

This is not a style preference. The user said it directly: their
own ability to detect plausible-but-unverified narrative is what
breaks down at the end of a long day. The rule has to do that work
instead.

#### Sub-sub-sub-rule: NEVER attribute a system event to a specific user input by temporal proximity alone

Closely related to the "no speculative explanation" family, this is
its own failure mode: when reporting that a logged event was caused
by a specific user payload — "Bernard's 'X' triggered turn Y",
"the message 'Z' produced this response", "the request_id N
corresponds to input M" — you MUST first verify the payload from
the same log line that names the event.

Anti-pattern: read a turn-end event at 14:26, notice the user typed
"lislisto" to Claude Code at 14:25, and conclude "Bernard's 'lislisto'
produced this turn." The two events are in different systems (Claude Code
chat ≠ Discord channel) and only coincide in wall-clock time. The actual
user text that entered the pipeline is in the turn-start event's text
preview for that same request id. Quote that, never the conversational text.

**Operational form:** before writing the sentence "the user's input
X caused event Y", run a query that returns the actual input
captured at intake (the turn-start text preview, a DB row, or
equivalent). If your sentence names a payload, the payload must come
from a log/DB read in the same response. If you only have a
wall-clock correlation, write "a turn fired at 14:25:49" — not
"your message 'X' fired at 14:25:49."

**Why this rule exists:** on 2026-05-14, during the Agent SDK
cutover verification, the assistant reported "Bernard's 'lislisto'
salió 100% por Agent SDK runner" based on a request_id timestamped
right after his "lislisto" in Claude Code chat. Bernard panicked —
he had typed "lislisto" only to Claude Code, never to Discord, and
for a moment thought the assistant had bridged the chats and was
sending his words to Insult without consent. The reality was an
unrelated Discord turn (text "Y sí solo es presumir jajaja remote
worker no es facil") that happened to fire ~10 seconds after his
Claude Code message. The damage was trust + adrenaline spike right
in the middle of a delicate revoke-API-key cutover. A 5-second
query against the turn-start text preview would have surfaced
the correct text and produced a non-alarming report.

The cost of guessing the payload is unbounded: at worst the user
believes the assistant has acted on their behalf without
authorization. Always quote the payload from the structured log,
never paraphrase from conversational context.

### Resilience anti-patterns — DO NOT introduce

These are codified after the 2026-05-08 outage post-mortem. Every entry is a
real failure mode that bit us or that production post-mortems documented. The
code that first fixed them died with `personas/` in 2f8d9ad, but every rule
applies verbatim to the live `persona_gateway/` turn path (which uses
discord.py the same way — see e.g. the guarded recovery send in
`persona_gateway/gateway.py::_dispatch`).

1. **`async with channel.typing(): await llm_or_other_long_call(...)`** —
   `Typing.__aenter__` makes a blocking `send_typing` HTTP request
   *before* the body runs. If the channel is hot, a 40062
   (`ServiceResourceIsBeingRateLimited`) here kills the entire turn
   even though the LLM never ran. Fix: typing is a fire-and-forget
   background task that wraps its own `HTTPException` (live:
   `persona_gateway/turns.py` typing keepalive). Reference:
   [discord.py context_managers.py:54-92](https://github.com/Rapptz/discord.py/blob/master/discord/context_managers.py).

2. **`except Exception: log + send(error_message)` without an inner
   try/except on the `send`** — when the exception was caused by the
   channel being rate-limited, the in-character error message also
   429s and the user sees nothing. Always wrap the recovery `send`
   with its own guard, and fall through to `message.add_reaction(...)`
   (different bucket, almost always survives) on secondary failure.
   Live implementation: `persona_gateway/gateway.py::_dispatch`.

3. **Stateless triviality filter for life-checks** — discarding
   "ups"/"okok"/"hola?" with no awareness of whether the previous
   turn failed is how the bot becomes invisible to a user trying to
   wake it. Any trivial gate must consult per-channel last-outcome state
   and bypass the skip when the previous turn failed within 60 s.

4. **Logging an event whose name lies about which stage failed** —
   an "llm_failed"-style event MUST NOT fire when the LLM never ran (e.g.,
   when typing exploded before the call). Failure stage is
   a typed field on the turn-end event, not buried in the event name.

5. **Ignoring `retry-after` from the upstream** — Anthropic returns
   `retry-after` in 429/529. Vercel AI SDK
   [#7247](https://github.com/vercel/ai/issues/7247) is the canonical
   anti-pattern (their retries collide on the worst possible second).
   Always honor the header when ≤ 60 s before falling through to
   jittered backoff.

6. **Out-of-character degradation text in user-facing error paths** —
   the persona DNA forbids exposing model identity. ChatGPT and Cursor
   send "model overloaded" text; we cannot. The live failure surface is
   neutral: the gateway sends "…" (or a reaction) on turn failure, never
   an error naming the underlying tech.

7. **Per-upstream circuit breaker for a single-upstream client** —
   Marc Brooker (AWS, author of the canonical jitter paper) explicitly
   advises against this in his [2022
   post](https://brooker.co.za/blog/2022/02/16/circuit-breakers.html):
   *"Circuit breakers are designed to turn partial failures into
   complete failures."* For a single upstream, opening
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
    before adding to the dependency set.

13. **Trusting a Discord error code from memory without verifying** —
    40060 is `InteractionHasAlreadyBeenAcknowledged` (slash commands),
    NOT a rate limit. 40062 is `ServiceResourceIsBeingRateLimited`.
    They are unrelated. Always verify against
    [discord-api-types RESTJSONErrorCodes](https://discord-api-types.dev/api/discord-api-types-v10/enum/RESTJSONErrorCodes)
    before quoting an error code as fact.

## Test surface — ALWAYS #general, NEVER the Insult DM

**Every real-contract bot verification runs in `#general` of the Khimeras server
(channel `1489180895264116736`), NOT in the direct-message channel with Insult.**

The DM (`@me/1489130575422820352`) is a TRAP for verification: it exercises the
simplest possible turn — single author, no other participants, no "Other People"
fact block, no multi-user batching, no cross-persona interplay. **It never
fails**, so a green DM reply proves almost nothing. `#general` is where the real
distortion lives (the multi-user context build, the behavioral guidance
assembly, host reception/routing), and it is where reported P0s actually
surface. Post-purga note: every persona is mention-gated, so the probe must
@mention the persona under test.

How to apply when driving Discord in the debug Chrome (`:9333`,
[[reference_discord_web_send_via_chrome]]):
- Open `https://discord.com/channels/<guild>/1489180895264116736` (#general),
  not the DM.
- Send the probe there, confirm the persona replies with the expected
  version tag (`khimeras_shared/version.py::VERSION_TAG`).
- A DM check is acceptable ONLY as a quick "is the process alive at all" smoke,
  never as the verification of record. If a fix is "verified", it was verified in
  #general.

**Why (2026-06-16):** the khimeras_shared deploy-gap P0 manifested in #general
(every turn fell over to ALICE there). The fix was first "verified" via the
Insult DM — which replied fine because the DM path is the one that never breaks.
Bernard: *"tú estás siempre probando Insult directo y eso pues nunca ha fallado"*.
The DM is the blind spot; #general is the test surface.

### "No quiero ensuciar la conversación viva de #general" NO es una excepción

The recurring escape hatch is to find a principled-sounding reason to fall back
to the DM. The 2026-06-18 variant: #general had a live, sensitive conversation
(Bernard ↔ Alex), so the slice A deploy was "verified" via the Insult DM "to
avoid polluting the thread." The reasoning FELT like Art. 8 (respect his
attention) but it is the same rationalization this rule exists to kill — a green
DM reply proves almost nothing, and "verified" must mean verified in #general.

Why the excuse is invalid: **#general IS the bot's testing channel.** A short
version-check probe ("despierto? confirma tu versión") is normal, expected
traffic there — Bernard and Alex probe the bot in #general constantly; it does
NOT "ruin" a thread. So:

- The default is ALWAYS a probe in #general, even when a conversation is in
  progress. A one-line version check is not pollution.
- If the thread is *genuinely* too sensitive to touch at that exact instant,
  the correct move is to **WAIT for a lull and then verify in #general**, OR
  report the verification as **still pending** — NEVER to substitute the DM and
  call the fix "verified." A DM smoke may confirm "the process is alive," but it
  is not the verification of record (the existing rule above).
- Respecting his live thread (Art. 8) and verifying on the real surface (Art. 2)
  are not in conflict: a brief #general probe satisfies both. Inventing a
  conflict to justify the easy DM path is the failure.

**Why (2026-06-18):** during the HOST 5/6 slice A deploy, I verified the new
revision (tag `ᵛ⁴·²¹·⁷⁶` + `shadow_router_decision` emitting) by probing the
Insult DM instead of #general, reasoning I shouldn't pollute Bernard's live
Mariposas-Negras conversation. Bernard: *"volviste a probar insult en la app, no
en el channel general."* Second recurrence of the same blind spot in two days.

### Don't ASK permission to enter the live thread either — it's a dilema vacío

The DM-substitute is one escape hatch; **asking permission to probe in the live
thread is the other.** Both dodge the same job. When a verification probe must go
into a live Bernard↔Alex conversation in #general, the probe IS authorized in
advance — do NOT close the turn with "¿le doy el probe, o lo mandas tú?" /
"¿entro a tu hilo o prefieres que…?". That is an empty dilemma (Art. 4 +
[[feedback_dont_open_dilemmas]]): entering the live thread to verify the bot is
**expected behavior, not an intrusion**, and the probe going out under
`bernard2389` (the only logged-in account on the debug Chrome) is part of what
"verify in #general" already means.

How to apply:
- Default to **driving the probe yourself** in #general, even mid-conversation —
  no permission ask. A bot probe is normal #general traffic (the rule above).
- If you're verifying a sibling (Vultur…), make the probe **on-topic** when you
  can — e.g. they're picking a movie, so ask Vultur (the film critic) for a rec.
  On-topic ≠ intrusive; it's the natural way in.
- The ONLY legitimate pause is the verifiable-state gate (Art. 2): if the new
  revision isn't serving yet (version tag still old / CD in flight), WAIT for the
  deploy and report it as pending — never ask *whether* to probe, only delay
  *until the build lands*. That's a real blocker, not a dilemma.

**Why (2026-06-29):** verifying Vultur's new "empedernido/enigmático" tuning after
the v4.21.109 merge, I correctly held the probe because the CD was still
in_progress (bot serving `ᵛ⁴·²¹·¹⁰⁸`) — but then closed the turn asking Bernard
"¿le doy con el pedido de rec a Vultur cuando termine, o lo mandas tú?" while he
and Alex were live picking a movie. Bernard: *"si métete a mi hilo con alex, es lo
esperado."* The deploy-wait was the right pause; the permission-ask was the empty
dilemma.

## E2E — the real contract (post-purga)

> **Historical note:** the old E2E sections here described `python -m insult
> run`, prefix commands (`!chat`, `!perfil`), an `E2E_TEST_MODE` cooldown
> bypass, and a Discord MCP server. All of that mechanism died with
> `personas/` in 2f8d9ad — there are no prefix commands and no local Insult
> process. Do not resurrect those steps.

The live E2E contract is:

1. Deploy (or run `python -m persona_gateway run` locally only when explicitly
   doing local dev — prod observation happens against the cloud, per
   [[feedback_observe_prod_not_local]] doctrine: never stand up a local bot to
   inspect prod).
2. Drive Discord web in the debug Chrome (`:9333`), probe in **#general** with
   an @mention of the persona under test.
3. Verify: reply arrives, in-character, correct language, expected
   `VERSION_TAG`, long replies chunked under Discord's cap
   (`persona_gateway/delivery.py::DISCORD_LIMIT = 1990`).
4. Memory: a follow-up probe referencing the earlier message confirms
   store→retrieve through Postgres.

## E2E via CI/CD Pipeline (Production Verification)

E2E testing means pushing code, triggering the full CI/CD pipeline, and monitoring the deployment to Azure. This is the real verification flow:

### Steps
1. Commit and push to `main`
2. CI runs (GitHub Actions: lint, tests, audit, security) — monitor with `gh run watch --exit-status`
3. On CI success, CD triggers automatically (workflow_run on CI completion)
4. CD detects which surfaces changed, builds the per-surface images
   (`persona-gateway`, `persona-runner`, `khimeras-host`) on the runner with
   buildx, pushes them to `ghcr.io/bernarduriza/discord-bot`, and deploys each
   changed Container App in `insult-rg`
5. Monitor CD deployment via `az` CLI:
   - `gh run list --workflow=cd.yml --limit=3` to check CD run status
   - `az containerapp show --name persona-gateway -g insult-rg --query "properties.latestRevisionName"` to verify new revision
   - `az containerapp logs show --name persona-gateway -g insult-rg --follow` to tail logs and confirm the gateway starts healthy
6. Once deployed, verify the persona responds in #general (version-tag probe via the debug Chrome)

### Key Resources
- **Registry**: `ghcr.io/bernarduriza/discord-bot` (`persona-gateway:<sha>`, `persona-runner:<sha>`, `khimeras-host:<sha>`, plus the content-addressed `khimeras-base` / `khimeras-runner-base`). No ACR since 2026-08-12 — see `architecture.md` § Registry.
- **Container Apps**: persona-gateway, persona-runner, khimeras-host (resource group: insult-rg); `discord-bot` retired at scale 0
- **CD workflow**: `.github/workflows/cd.yml` — triggers on CI success on main
