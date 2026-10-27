# 52 — The ChatGPT plan is already paid: run OpenAI turns on it through Codex, not on metered tokens

Status: **In progress** — the backend shipped 2026-10-26 (`agent_sdk/codex.py`, tests) and AIRE runs on this Mac as a launchd agent the same day (`infra/install-mac.sh`, verified through its real door); what stays open is videopipe calling it.
Proposed: 2026-10-26 by Bernard (*"así como se puede usar Codex y Claude para mí, que también se utilice esta cuenta para no estar utilizando todo el tiempo los tokens de OpenAI y estarme gastándolos cuando ya tengo incluso posibilidad de usar Astra directamente"*); greenlit the same day (*"go"*).

## What it is

Bernard pays a ChatGPT plan (`plan_type: prolite` per the login's id token, active until
2026-11-27). Codex CLI signed in with that account runs GPT-6 Astra headlessly on the plan's
quota, with no API key and no per-token bill. Every OpenAI turn that is Bernard's own work
should run there first; metered tokens (Azure OpenAI, #51; `insult-openai`) only when the
plan cannot serve it.

## Decided by Bernard 2026-10-26

- **The box is this Mac** (*"backlog para esta mac"*): AIRE spawns the Codex agent here, signed
  in with Bernard's ChatGPT plan; the droplet stays out of it (#49 item 2).
- **Codex is never used directly** — *"DESINSTALA CODEX AHORA, y solo debes usar el coagente de
  guion astra, a través de AIRE"* (`codex logout` + `npm uninstall -g @openai/codex` the same
  hour, after one direct run had produced videopipe's `script-vidrios.js`). The binary lives
  only as AIRE's agent, at `~/.aire/codex/node_modules/.bin/codex` (npm prefix, off the PATH),
  logged in with the plan; `AIRE_CODEX_COMMAND` names that path.
- **Every Astra turn goes through AIRE**, the videopipe script coagent first (GPT-6 Astra Medium,
  its hard rule). Until AIRE runs on this Mac as a service, videopipe has no script transport:
  no Codex direct, and scraping chatgpt.com is out on the Terms.

## What shipped (2026-10-26)

- `agent_sdk/codex.py` + `codex_options.py` + `codex_process.py` + `codex_events.py`: a
  third backend behind the `agent_sdk` frontier. `TurnSpec.provider = "codex"`; the operator
  enables it with `AIRE_CODEX_COMMAND` (the binary) — the name exists on the wire only where
  the box has it, the roster's trust split. One `codex exec --json` process per turn,
  `exec resume <thread>` after the first; `-m` from `spec.model` (default `gpt-6-astra`,
  `AIRE_CODEX_MODEL`), effort `medium` (`AIRE_CODEX_EFFORT`); `agent` mode →
  `sandbox_mode=workspace-write`, anything else read-only; `approval_policy=never`.
- The pen is `acp_mirror` (the table is the agent log, not an ACP one): prompt, thread
  binding, every `item.*`, the result with its usage. The AIRE session → Codex thread map
  lives there; `engine.has_session` already answers through it for any non-Claude provider.
  A resume the box has no rollout for reopens fresh and logs `CODEX-RESUME-LOST` (the #49
  cold-resume law); a failed turn is `error_turn_failed`, a silent exit `error_exit_<code>`
  — never text.
- **Its own credential chain** (superseded 2026-10-27 by #53; as shipped on 10-26 it was a
  `ROTOR = False` flag and a `NOMINAL = True` client): a Codex turn rides the rotor's `codex/*`
  slots — the plan seat (`CODEX_HOME`) first, a metered `CODEX_API_KEY` behind it — and an
  all-dry Claude chain never refuses it, because each provider's chain dries alone.
- **Money, honestly**: the slot decides (`slot.metered`): a plan turn's `aire_spend` row says
  `metered=false`. Codex reports tokens, never dollars, so #53 prices them at OpenAI list — a
  plan turn now leaves a nominal row (it left none on 10-26), a fallback turn a real one. The
  "metered tokens only as fallback" promise above is implemented there.
- Images ride as files (`-i`), text documents inline; a PDF is refused by the door for any
  non-Claude provider, as before. Codex's `input_tokens` includes the cached part; the backend
  subtracts it so the usage keys mean the same as Anthropic's.
- Tests: `tests/test_codex_backend.py` against `tests/fake_codex.py` — a real
  `codex exec --json` process with a fake model (argv dial, warm resume, cold resume LOUD,
  failure shapes, modes sandbox, weights per turn, images, the provider listing). 411 green.
- The droplet gets nothing: no bootstrap step, no `/etc/aire/env` knob (Bernard's decision).

## Verified 2026-10-26 (this Mac, $0)

- `codex login` redone for AIRE's agent (Google SSO driven in the debug Chrome) →
  `Logged in using ChatGPT`, `~/.codex/auth.json`.
- **Through the real door** (`uvicorn aire.server:app` on 127.0.0.1:8089 with
  `AIRE_CODEX_COMMAND`, `POST /projects/videopipe/sessions/<s>/messages`,
  `{"provider": "codex", "mode": "complete"}`): SSE `text` → `result`
  (`model: gpt-6-astra`, `subtype: success`, 1,933 uncached + 12,160 cached input, 5 out)
  → `done`; a second turn on the same session resumed the same Codex thread
  (`session_id` identical) and answered the word from the first; `provider: "gemini"` → 422.
- `/health` `{"status":"ok","memory":"postgres"}`; a Codex process peaks ~205 MB RSS.
- **The ACP road is dead for now**: `codex-acp` 0.16.0 (2026-06-08, codex-core rust-v0.137.0)
  opens the session but the backend answers *"The 'gpt-6-astra' model requires a newer
  version of Codex"* (and `gpt-5.5` *"not supported … with a ChatGPT account"*).
  `codex exec --json` IS the sanctioned surface: it is what the official `@openai/codex-sdk`
  runs underneath. Re-measure ACP when Zed ships a newer adapter.
- Every turn carries ~14 K input tokens of Codex's own preamble; `--ignore-user-config
  --ignore-rules` did not change it; 86 % of it rides the cache.

## Why (the money and the terms)

- The ChatGPT subscription includes **no API credit**; the API is billed apart.
  `insult-openai` cost USD 81 in eight days (#51) on tokens the plan could have covered.
- Pro plans have **no five-hour limit** in Codex (weekly limits may apply), per
  learn.chatgpt.com/docs/pricing.
- The ChatGPT Terms of Use (2026-01-01) forbid *"Automatically or programmatically extract
  data or Output"*: scraping chatgpt.com (videopipe's `coagent.mjs`) is the wrong road;
  Codex is OpenAI's own client and the sanctioned one.

## What stays open

1. ~~AIRE as a service on this Mac~~ **Done 2026-10-26**: `infra/install-mac.sh` lays
   AIRE down under `~/.aire` as the launchd agent `com.bernarduriza.aire` (sparse
   checkout, venv, the Codex agent, env from `~/.secrets/`, `/health` verified). Receipt
   through that door: two `provider: "codex"` turns on one session, `pong` then the
   recalled `pong`, same Codex thread, `gpt-6-astra`, `success`; the mirror rows landed
   in the OWNER's Postgres on Azure (the Mac is admitted as role `aire`), zero
   `aire_spend` rows; `kill <pid>` → launchd brought it back in 4 s. The Mac still
   sleeps after one idle minute — the consumer sleeps with it, so nothing is lost
   that a human was waiting on.
2. **videopipe's script coagent** calls that door with `provider: "codex"` (its own repo).
3. **Exhaustion signal.** When the weekly limit hits, what Codex emits is not measured. Today
   a provider error surfaces as `turn.failed` → `error_turn_failed` (mirrored, logged),
   never as text; the rotor (#31) must learn the shape before this carries a fleet.
4. **Streaming**: `exec --json` emits the agent message whole (`item.completed`) — a consumer
   sees `text` once, then `result`. Live tokens would need `codex app-server`; not built until
   a consumer asks.
5. **Who may use it.** The plan is Bernard's personal account: his own consumers yes.
   Reselling it to invited keys (#51's clients) is NOT this item: third-party use of a ChatGPT
   plan is "Sign in with ChatGPT", a limited partner trial today
   (developers.openai.com/siwc/quickstart).
6. Images out: Codex generates with `gpt-image-2` on the same quota (`$imagegen`); whether
   it works inside `codex exec` is not verified.
