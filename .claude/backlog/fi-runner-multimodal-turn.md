# FI-RUNNER-MULTIMODAL-1 — image/document input as a first-class fi-runner turn primitive

Status: Proposed
Proposed: 2026-07-05 by Bernard (discovered images work in discord-bot only via a consumer-local bypass of fi-runner; the shared turn contract silently discards them)

## What it is

fi-runner's turn contract is **text-only**: `Runner.run(user_message: str)`
(`runner.py:170`) and `Backend.run_turn(user_message: str)` (`backend.py:289`) take
a plain string. `ClaudeCodeBackend` calls `client.query(user_message)` with that
string (`claude_code.py:225,238`) — and the Claude Agent SDK's `query(str)` branch
wraps the string into a **text-only** user message, **silently discarding any image
or document blocks**. `CodexBackend` concatenates strings too (`codex.py:157`).
`vision` exists in fi-runner ONLY as a model-capability FLAG
(`fi_runner/models/contracts.py:23`, `config.py:318`) — metadata about which models
CAN see; there is zero plumbing to actually send an image.

Consequence: a runner cannot accept multimodal input through the framework. Every
consumer that needs vision must reach AROUND fi-runner and talk to the SDK directly.

## The proven canary (Art. 6 — this is why the extraction is justified, NOT premature)

discord-bot ALREADY hit this wall and built the workaround **in production**
(v3.9.43, "REWRITE-B1"). It is the canonical reference to elevate:

- **Symptom that forced it** (`khimeras_shared/runner/agent_client.py:117-120`):
  *"Alex sent text+2 images, Insult ignored the images entirely"* — the old
  text-only extractor discarded the image blocks.
- **The attachment contract** (`agent_client.py:110-128`): extract the raw
  **Anthropic-shaped content blocks** whose `type ∈ {"image","document"}` from the
  last user message, forward them as a separate `attachments` field to the runner.
- **The dual path** (`personas/insult/agent/runner.py:769-789`): when
  `req.attachments` is present, build `content_blocks = [{"type":"text",...}, *attachments]`,
  wrap in a streaming user message `{"role":"user","content":content_blocks}`, and
  hand the SDK an `AsyncIterable` to `query()` — bypassing `ClaudeCodeBackend.run_turn`
  entirely. Text-only turns keep the plain-string path.
- Metric `agent_runner_image_turns` (`personas/insult/core/metrics.py:55`) tracks it.

This is the framework-first-canary trigger in its "elevate once PROVEN" form — the
opposite of [[og118-real-background-execution]] / discord-bot cross-turn jobs, where
no consumer had built the pattern yet so abstracting was premature. Here the pattern
exists, works, is in prod, and is being re-rolled per consumer.

## Canonical path to reuse (Art. 6)

Lift discord-bot's dual path INTO `ClaudeCodeBackend` (and the `Runner`/`Backend`
contract), so the framework owns the text-vs-multimodal branch:

1. Add an optional `attachments: list[dict] | None` (Anthropic-shaped image/document
   content blocks) to `Backend.run_turn` / `run_turn_stream` and `Runner.run` /
   `run_stream`. Default None → byte-identical text-only path (zero regression).
2. In `ClaudeCodeBackend`, when attachments are present, build the multimodal
   streaming `{"role":"user","content":[text, *attachments]}` and pass the
   `AsyncIterable` to `client.query()` — exactly discord-bot's dual path, now framework-owned.
3. Keep `CodexBackend` text-only (or raise a clear "backend has no vision" error when
   attachments are passed to a non-vision backend — the `vision` model FLAG becomes
   the guard).
4. Migrate discord-bot to call the framework and **delete its bypass** (the canary
   collapses back into the framework). og118 gains image input for free (today it only
   does text + document-RAG); alice/ferboli inherit vision.

## The decision that's the owner's

Whether to build it and when. It's a real framework-contract change touching every
runner + both backends, so it's a per-level GO. Low risk (additive, default-None,
text path unchanged), high reuse. Sequence it against discord-bot's own in-flight
work so the bypass-deletion lands after the framework carries it.

## Status / next step

Not built. Feasibility is proven (the canary runs in prod). Unblock = Bernard's GO.
See [[framework-first-canary]] (the rule this instantiates) and the discord-bot
persona-runner as the reference implementation.
