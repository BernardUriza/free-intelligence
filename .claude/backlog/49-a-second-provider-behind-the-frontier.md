# 49 — A second provider behind the frontier (Qwen Code), chosen per turn

Status: **In progress** — the ACP backend shipped 2026-09-17 (code, tests, docs; verified end to end on the Mac); the founding consumer waits for the NUC.
Proposed: 2026-09-17 by Bernard (*"¿se puede poner qwen code como otro agent sin romper nada, y que el consumer elija?"*); greenlit the same day as ONE adapter, not one per vendor: *"un solo adaptador `agent_sdk/acp.py`… y en el futuro compraré una NUC buena para tener en casa y ya"*.

## What shipped (2026-09-17)

- `agent_sdk/acp.py` + `acp_bridge.py` + `acp_messages.py` + `acp_roster.py`: one
  backend for every agent in the ACP registry (40+: Claude, Codex, Gemini, Qwen,
  Kimi, Mistral, Grok, MiniMax, GLM, opencode, goose, …). `TurnSpec.provider`
  names it; `AIRE_ACP_AGENTS` (operator env, JSON) says what a name runs; the
  door validates and 422s the rest. `backend_for(provider).build_options(Birth)`
  is the seam — `core.py` never learned a vendor's name.
- `aire/acp_mirror.py`: the pen for ACP turns — `aire_agent_log`, every
  `session/update`, prompt and stop reason appended eagerly, plus the
  AIRE-session → agent-session mapping that makes `session/load` possible.
- `drain.py` unchanged: the backend yields classes with the SDK's names.
- Tests: a real ACP agent over real stdio inside pytest (`tests/fake_acp_agent.py`,
  memory on disk) covering text, tools allowed/rejected by mode, warm resume
  without replay, cold resume LOUD, cost from `usage_update`, the roster.
- E2E on the Mac through `POST …/messages` with `provider: "claude-acp"`
  (`claude-code-acp` 0.16.2): SSE `text` → `result` (`model: "claude-acp"`), and
  after a forced rebind the new client loaded the same agent session and answered
  "pong" to *what did you reply before* — one `session` row in the mirror.

## What stays open

1. **Cold resume re-priming**: on a fresh box the agent cannot `session/load`; the
   mirror holds the transcript but ACP has no import. Render the mirrored turns
   into the first prompt of the fresh session (bounded), or accept per-session
   provider binding as final. Bernard's call.
2. **The droplet cannot host `claude-code-acp`**: no node installed, 162 MB free,
   and the adapter adds ~90 MB of node beside the `claude` it spawns (measured
   2026-09-17). The backend deploys without a roster (zero behaviour change).
3. **The NUC is the founding consumer's home** — but ACP is stdio, so AIRE must
   spawn the agent on the same box: either AIRE runs on the NUC, or the backend
   grows the SDK's HTTP/WebSocket transport (`connect_to_agent(client, transport)`)
   to reach an agent served from the NUC. Pick when the NUC exists.
4. `usage`/cost: `claude-code-acp` reports none; other agents may. `prices.json`
   stays Anthropic-only until a provider reports tokens without dollars.
5. The vetted in-process tool registry does not mount on an ACP turn (ACP agents
   bring their own tools); only HTTP remote tools (#48) could.

## What it is

`TurnSpec` gains `provider: str = "claude"`; the door validates it against
`agent_sdk._BACKENDS`; `core._client_for` stops hardcoding `SDKClient("claude", …)`.
Because `TurnSpec` is compared whole at `_rebind` (#38), a turn naming a different
provider already drops the warm client — the seam `ec4fa12` built is real, and the
engine never learns the second name.

## What was verified 2026-09-17 (this Mac, `qwen` 0.24.0, $0 spent)

- **Qwen Code speaks Claude Code's wire format.** `--output-format stream-json`
  emits `system/init`, `stream_event`, `assistant` (`message.content` blocks) and
  `result` (`subtype`, `session_id`, `usage`, `is_error`, `permission_denials`).
  `--input-format stream-json`, `--session-id`, `--resume`, `--channel SDK`,
  `--approval-mode plan|default|auto-edit|yolo`, `--acp` all exist.
- **A Python SDK exists**: `qwen-code-sdk` 0.1.0rc0 (PyPI). `query(prompt, options)`,
  `can_use_tool` async callback (a cage), `set_model`, multi-turn via
  `AsyncIterable`. It yields **dicts**, not dataclasses: `drain.py` types by
  `type(m).__name__` (`AssistantMessage`, `TextBlock`, `ResultMessage`), so the
  backend module owns a thin dict→object adapter. Its own scope note: no ACP
  transport, **no in-process MCP servers** — the vetted registry (`memory`,
  `corpus`, `persona`, `tracker`) cannot mount on a Qwen turn; only HTTP remote
  tools (#48) could.
- **No `session_store`.** Qwen writes `~/.qwen/projects/<cwd-hash>/chats/<id>.jsonl`
  in Gemini-CLI shape (`message.parts`, not `content` blocks) on the box's mortal
  disk. This is the litmus test failing: a Qwen turn gives the agent a body back
  until AIRE owns the mirror itself (append the stream to Postgres; rematerialize
  the jsonl before `--resume` on a cold box — `restore.py` already does this for
  the SSH door).
- **Qwen's OAuth free tier was discontinued 2026-04-15.** The CLI now needs a
  Coding Plan, OpenRouter, Fireworks, or any OpenAI-compatible endpoint
  (`--auth-type openai` + `OPENAI_BASE_URL/KEY/MODEL`). The local CLI was 0.10.3
  with an expired token; updated to 0.24.0 to get the current auth surface.
- **Semantics, same 5-item test** (lexical disambiguation, entailment, Winograd
  coreference, double-negation paraphrase, sarcasm):
  - Qwen3.7-Plus on chat.qwen.ai (Bernard's account, $0): **5/5**.
  - `qwen3.5:4b` (Ollama, Q4) through the Qwen Code harness: **0/5** — it ignored
    the prompt and confabulated a coding task (*"Looking at `src/auth.py`…"*),
    163 s, 6,150 input tokens (the harness's system prompt), and the result said
    `subtype: success`. The #23/#31 lying-green family, on a new provider.

## What it costs, honestly

1. Wiring (provider field, backend module, adapter): small — the frontier did
   its job.
2. **Memory**: the actual work. Two transcript formats, two resume paths. A
   session served by Claude one turn and Qwen the next does NOT share memory
   unless AIRE renders one transcript into the other's prompt. So the honest
   first shape is **provider bound per SESSION at birth**; per-turn switching
   with shared memory is a second item.
3. Credentials: the rotor (#31) and `limit_hit` are Anthropic-shaped; a Qwen
   slot is its own env set, and its exhaustion signal is unknown until measured.
4. Pricing: `prices.json` is Anthropic-only; `aire_spend` needs a row shape for
   a provider whose cost may be $0 (self-hosted) or per-token (Coding Plan).

## The decision that's the owner's

There is no $0 Qwen the droplet can reach: the free tier is dead, and Ollama
cannot run on 512 MB (`qwen3.5:4b` alone is 3.4 GB). A Qwen backend on AIRE
therefore means either a paid endpoint — and the standing law is that a $0
balance is the spend cap, never a slot to fund — or a self-hosted model on a
machine that is not the droplet, which makes the daemon depend on that
machine being up (a body). Until one of those is chosen, this item stays
Proposed, not blocked-on-code.
