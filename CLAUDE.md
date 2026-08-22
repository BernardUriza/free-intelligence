# AIRE — context for agents

**A**rtificial **I**ntelligence **R**eflector **E**nvelope. An HTTP server that wraps
the Claude Agent SDK and mirrors each session's transcript to Postgres.

**This is a MONOREPO** (backlog #20, 2026-07-20): `server/` is the daemon — the
pen, role `aire`, deployed to the DigitalOcean droplet by
`.github/workflows/deploy-server.yml`; `front/` is the waiter — read-only, role
`aire_reader`, Next.js SSR on Azure Container Apps, deployed by its own
path-filtered workflow. One repo, still two deployments and two credentials:
the CQRS wall is credential-and-pipeline, not folder. **The front NEVER rides
to the droplet**: the body clones partial+sparse and materializes `server/`
only (Bernard's law, 2026-07-20). And **`aire` is a reserved project name** —
AIRE is the structure that contains conversations, never a project itself
(enforced in `server/aire/names.py`). Everything below this line describes the
SERVER half; the front's law rides in
`front/.claude/rules/read-only-waiter.md`.

The story — the Mecano song, the EC-GPS blueprint, the log-is-truth science — lives in
[`server/docs/genesis.md`](server/docs/genesis.md); the competitive pitch in
[`server/docs/thesis.md`](server/docs/thesis.md). This file is only what an agent needs to ACT.

**The litmus test for every design decision** (from the genesis):

> *Does this give the agent a body back? Then no.*

Everything below was **verified against the source code of the installed SDK**
(`claude-agent-sdk` 0.2.116) or by observing the running system — never against
memory. To contradict anything here, verify it first the same way.

## The decisions, already made

1. **AIRE is a SERVICE, not a library.** You don't import it: you call it over HTTP.
   The SDK lives in one place, the Postgres credentials live in one place, any
   language can talk to it.
0. **THE DAEMON HAS NO FACE — it never returns HTML. Not one byte, not ever.**
   Bernard's settled conclusion (re-affirmed 2026-07-14 after an SSR page briefly
   shipped here and scared him — that surface was reverted the same hour). The old
   "the server is the interface / streaming SSR" thesis is DEAD in this repo: the
   daemon's only mouths are `/health` (JSON), the message endpoint (SSE events),
   and — since 2026-08-07 (backlog #30) — the gateway door (`/v1/*`), which only
   relays Anthropic's own JSON/SSE byte-for-byte and never renders anything.
   **Every human-facing view — live or stored — lives in [`front/`](front/)**
   (this monorepo's other half, live on Container Apps), which may render the
   daemon's SSE stream however it wants. Do not re-propose SSR-from-the-daemon
   (Art. 7).
0b. **The gateway door is auth-pass-through EXCEPT for an invited key** (2026-08-11,
   backlog #32). A caller carrying their own Anthropic credential is relayed and
   AIRE spends nothing on them. An invited key has no credential by construction —
   that is what being invited means — so for those callers AIRE lends its OWN
   (`aire/lending.py`) and prices the turn from tokens (`aire/pricing.py` +
   `prices.json`), because Anthropic reports tokens and a ceiling needs dollars.
   **The lent credential has its own named slot** — `AIRE_LEND_OAUTH_TOKEN`, or
   `AIRE_LEND_API_KEY` when a metered key exists (preferred). It deliberately
   does NOT read the engine's `CLAUDE_CODE_OAUTH_TOKEN`, though provisioning
   derives both from the same secrets file today: one OAuth exists per account,
   so the value is the same. The slot is what makes the value *chosen* — lending
   switches off by clearing one variable while the engine keeps dispatching, and
   no unrelated credential that lands in the environment can silently become what
   AIRE hands to strangers. Two facts to keep before touching this: that shared
   value means an invited key burning the weekly pool **starves the engine too**
   (the coupling #31's rotor exists to survive, and the argument for a metered
   key); and an OAuth token is refused by `/v1/messages` unless `anthropic-beta:
   oauth-2025-04-20` rides with it, appended to whatever betas the caller sent.
2. **One database, one `project_key` per project.** The SDK's `SessionKey` already
   carries `project_key`; its docstring says *"Multi-tenant deployments should set this."*
3. **The memory (transcript) goes to Postgres. The work does NOT go to git — AIRE
   doesn't touch git.** Not yet: AIRE is not defined as a code agent. EC-GPS never
   used git either — artifacts were downloaded by hand for analysis, and **at this
   level that is the design, not a gap.** If git ever enters, it enters as a **tool
   configured FROM OUTSIDE, at the user layer** — an MCP wired in via the API with the
   *user's own account* (personal or work), never as an identity baked into the server.
4. **The container stores nothing.** `CLAUDE_CONFIG_DIR=/tmp`.
5. **The `server/` half is WRITE-ONLY toward the database.** Every read —
   rendering, analytics, dashboards, session browsing — lives in
   [`front/`](front/) (the PHP of EC-GPS, Next.js SSR,
   [live](https://aire.bernarduriza.com);
   backlog #15, merged here by #20). Its `/claude` view is the one Bernard
   asked for: a link per folder → its sessions → the transcript rendered as
   Claude Code reads. The sanctioned exceptions here are the SDK's
   `session_store.load()` for resume (the agent reading its own memory) and the
   device roster the socket must enforce. Full law:
   [`.claude/rules/write-only-daemon.md`](.claude/rules/write-only-daemon.md).
   **The one thing the front makes THIS repo's problem:** the reader (`aire_reader`,
   `GRANT SELECT` only) sees *future* tables through
   `ALTER DEFAULT PRIVILEGES FOR ROLE aire`. So the engine must create
   `claude_session_store` **as `aire`** — as any other role, and the console goes
   blind to it. (The console itself is now behind HTTP Basic and connects with a
   credential that cannot write; the daemon keeps the pen alone.)

## Reuse, don't rewrite

- **The Postgres store**: copied from the SDK's official
  `examples/session_stores/postgres_session_store.py` → [`aire/store.py`](server/aire/store.py)
  (two marked adaptations: uuid-dedup in `append()`, lazy-asyncpg factory).
  **Conformance suite green** (2026-07-13): all contracts of
  `claude_agent_sdk.testing.run_session_store_conformance` passed against local
  Postgres.
- **The HTTP server pattern**: `claude_agent_sdk/hosting/` in
  [claude-cookbooks](https://github.com/anthropics/claude-cookbooks) is the reference
  (FastAPI + SSE + Bearer auth). AIRE's [`aire/server.py`](server/aire/server.py) opens the
  axis the cookbook lacks: `POST /projects/{project}/sessions/{session}/messages`
  (the cookbook hardcodes one project, `cwd="/app"`). Names map to SDK UUIDs via
  `uuid5` ([`aire/keys.py`](server/aire/keys.py)) — no mapping table.

## Verified SDK facts (don't re-discover them)

- **`session_id` CAN be set.** `subprocess_cli.py:355` → `cmd.extend(["--session-id", ...])`.
  **No mapping table needed** from external id to SDK id.
- **`session_store` and `enable_file_checkpointing` are INCOMPATIBLE.** The SDK raises
  `ValueError` (`session_store_validation.py`): *"checkpoints are local-disk only and
  would diverge from the mirrored transcript."* → **No `rewind_files()`. The workdir is
  scratch; artifacts worth keeping are fetched by hand (decision #3).** The day git
  exists as a user-layer MCP, branches would take that role — not yet.
- **`session_store` is a mirror, not a replacement.** The subprocess keeps writing the
  JSONL to disk; the adapter receives **a secondary copy**. On resume, the SDK loads
  from the store and materializes it into a temp dir with `CLAUDE_CONFIG_DIR`.
- **`session_store_flush='eager'`** writes each entry immediately → no loss window if
  the container dies. `'batched'` is faster but can lose.
- **`continue_conversation` + `session_store` requires `list_sessions()`** implemented.
- **Only `append()` and `load()` are mandatory** in the Protocol; the other four are
  optional and the SDK probes them at runtime.
- **There are two distinct memories**: `SessionStore` (raw transcript) and the
  **Memory Tool** (`memory_20250818`, distilled facts, client-side → your same database).
- **`SandboxSettings` confines ONLY bash, NOT `Read`/`Grep`/`Write`** — verified in
  the SDK source 2026-07-20, correcting the earlier claim here. Its own docstring:
  *"Filesystem read restrictions: Use Read deny rules … not these sandbox settings."*
  The real filesystem cage for an agent is the **`can_use_tool`** callback (a
  per-tool allow/deny gate) or permission deny rules — wired in `engine/cage.py`,
  scoping every file tool to the session's casita.
- **`Stop` hook** → where end-of-job actions go. (The old `git commit && push` idea is
  parked until git exists as a user-layer MCP — see backlog #12; today: nothing.)
- **`max_budget_usd` caps the CLIENT, NOT the query** — measured 2026-07-20 on the
  droplet, contradicting the obvious reading. A pooled `ClaudeSDKClient` that reaches
  the ceiling is **poisoned**: every later turn dies instantly with an EMPTY `result`
  (0 output tokens, no tool calls, the same cost echoed back) and **no error event**,
  so a cut turn is indistinguishable from success. Dropping the pool revives it.
  Backlog #23.
- **`permission_mode="bypassPermissions"` is REFUSED when the process runs as root**
  (the same guard as the CLI's `--dangerously-skip-permissions`), and the daemon runs
  as root: it made every `mode=agent` turn die with `ProcessError` exit 1 while
  `mode=complete` stayed green — a defect invisible to `/health`. `acceptEdits` is the
  mode that works, and it honours `allowed_tools`, which bypass left decorative.
- **A session name that is already a UUID must be honoured verbatim** (`keys.py`), and a
  project may name an EXISTING casita (128-char allowlist). That is what lets the AIRE
  door continue a session the CLI started: same `cwd` → same `project_key` → the store
  finds the memory. **One memory, two doors** — verified live 2026-07-20.
- **Claude Code is a first-class gateway client** (verified 2026-08-07 against the
  published [gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol)):
  `ANTHROPIC_BASE_URL` points it at any Anthropic-format endpoint; only
  `POST /v1/messages` is required; `anthropic-beta` must be forwarded verbatim
  (never allowlisted); error bodies must relay unwrapped (the CLI pattern-matches
  their wording to auto-retry); a 300s byte watchdog counts SSE pings, so a proxy
  that buffers or swallows them aborts streams mid-thinking. That contract is what
  the **gateway door** (`aire/gateway.py`, backlog #30) implements — a third door,
  auth-pass-through, mirrored to `aire_gateway_log` (created as `aire`, so the
  reader sees it). The SDK spawns the CLI with an env inherited from `os.environ`
  (`subprocess_cli.py:431`), so `engine/options.py` pins every spawned CLI's
  `ANTHROPIC_BASE_URL` to `api.anthropic.com` — the gateway can never recurse.
- **A burned weekly pool returns a LYING SUCCESS, not an error** — measured live
  2026-08-07: result text "You've hit your weekly limit · resets …", usage all
  zeros, `total_cost_usd: 0`. Same family as the #23 budget lie. The engine's
  credential rotor (`engine/credentials.py` + `turn.py`, backlog #31) detects it
  (phrase AND zero usage, both required), logs `CREDENTIAL-EXHAUSTED`, rotates
  `primary → backup → metered API key` with a 1h cooldown, and emits a real
  `credentials_exhausted` error when all slots are dry. The API-key slot works
  headless: `ANTHROPIC_API_KEY` set + `CLAUDE_CODE_OAUTH_TOKEN=""` dispatches
  with no interactive approval. Backup slots activate the moment their env vars
  appear in `/etc/aire/env`; two OAuth tokens from the SAME account share one
  pool — a same-account backup is a placebo.

## Discarded routes (don't re-propose them)

- **Ephemeral VM with SSH** (the original `air-lite`): the Agent SDK reinvented with
  `boto3` + `paramiko`. Dead.
- **Persistent VM ("never terminate")**: reinvents git as storage and pays 24/7 rent
  for a disk that is a single point of failure. Dead.
- **Managed Agents** (Anthropic's hosted offering): the memory lives on their side, no
  `session_store`, not ZDR-eligible, charges $0.08/session-hour on top of tokens. Dead
  for this use case.
- **Adopting Agno**: its `ClaudeAgent` doesn't pass `session_store` (verified: 0
  occurrences) and maps sessions in an in-RAM `Dict` → loses `resume` on restart.
- **Adopting ArcReel**: AGPL-3.0 (viral) and its `DbSessionStore` is an internal lib,
  not a callable service.
- **Azure for the droplet**: the whole burstable B-series was blocked at subscription
  level (28 attempts, 7 regions). The daemon lives on DigitalOcean — budget law in
  [`.claude/rules/do-budget.md`](.claude/rules/do-budget.md).

## How to work here

- **English only.** Every byte committed to this repo is written in English — see
  [`.claude/rules/english-only.md`](.claude/rules/english-only.md).
- **The log is the truth.** Touching memory or rendering? Read
  [`.claude/rules/log-is-the-truth.md`](.claude/rules/log-is-the-truth.md) first.
- **The device verbs (MKDIR/ALLOW/REVOKE) and the whitelist** are a frozen
  contract with a persistence model — see
  [`.claude/rules/device-verb-protocol.md`](.claude/rules/device-verb-protocol.md).
- **No `.py`/`.sh`/`.yml` file over 30 lines** — the thirty-line law, specific to
  this repo: [`.claude/rules/thirty-line-law.md`](.claude/rules/thirty-line-law.md).
- **NEVER drive the daemon by SSH — reaching for it means an endpoint is
  missing, so build the endpoint and use it.** SSH may operate the body (and it
  is Bernard's own terminal door); it is never how an agent talks to the brain:
  [`.claude/rules/ssh-is-a-missing-endpoint.md`](.claude/rules/ssh-is-a-missing-endpoint.md).
- **Verify against the code, not the docs and not your memory.** This repo already
  produced three false claims that only source code disproved.
- **Bernard distinguishes learning from building.** When he is understanding something,
  don't rush ahead writing code: you would be stealing it from him. The droplet is
  deliberately his Linux curriculum — show the raw surface (SSH, `systemctl`,
  `journalctl`), don't wrap it away. Ask if it isn't obvious which mode is active.
- **What's built vs what's next**: the honest status table is in the
  [README](README.md#status--honest); the roadmap is
  [`.claude/backlog/`](.claude/backlog/README.md).
