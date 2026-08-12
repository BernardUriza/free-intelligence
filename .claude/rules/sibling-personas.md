# Sibling Personas — Durable Host, Not an Ephemeral Local Process

Sibling personas (Vultur, and any future one) are NOT Insult. They share ONE
brain — the persona-runner — addressed by `persona_id`, and each runs as its own
Discord bot user under `persona_gateway`. **Post-purga (2026-07-14): EVERY persona,
Insult included, is mention-gated via `should_respond` (`aliases=[]` makes Insult
@mention-only). NO persona answers unaddressed general chatter right now — Insult's
omnipresence died with the `personas/insult` monolith and RETURNS only when the
demux_ai host (#6) owns reception and routes.** The `registry.py` comment on the
Insult entry is the source of truth ("Mention-gated vía gateway por ahora; su
omnipresencia regresa cuando el host nuevo sea dueño de la recepción").

## The hard rule: a sibling persona needs a durable Azure home

**Every sibling persona MUST run from a durable Azure Container App, cloned from
the `alice-bot` pattern — NEVER as a hand-started ephemeral process on Bernard's
Mac.** An ephemeral local gateway dies silently on a Mac restart, a sleep, or a
trimmed `.env`, and the bot just goes mute with ZERO signal. This is the same
fragility class as Arbor TTS (`voice.md`) — and it is the documented root cause
of the "Vultur no responde" incident (2026-06-16).

The durable host is `persona-gateway`:

- **`Dockerfile.gateway`** clones `Dockerfile.alice` **minus the codex/node
  layer** — the gateway runs NO LLM of its own; it is a thin HTTP client of the
  persona-runner (`AgentRunnerClient` → `/v1/turn`). It COPYs `persona_gateway/` +
  `khimeras_shared/` + `shared/` (its real import graph), guarded against the
  ModuleNotFound copy-gap class by
  `tests/arch/test_runner_dockerfile_copies_imports.py`.
- **Container App**: `prod-env`, **`minReplicas=maxReplicas=1`** — and BOTH
  halves are load-bearing, for opposite reasons. `max=1`: a Discord bot with >1
  replica connects N times and posts DUPLICATE replies. `min=1`: the gateway
  HOLDS each persona's Discord websocket, and a DM never issues an `/invite`
  that could wake it (Discord isolates DM channels per bot user, so the host
  cannot see a DM — `persona_gateway/routing.py::should_respond`). Scaled to
  zero the personas are offline and every DM dies unheard — the 2026-07-27 "en
  su app no contestan" incident through a different door. **`min=1` here is a
  product requirement, not a cost oversight**: it survived a 2026-08-12 cost
  sweep that took every other app in the subscription to `min=0`, and the
  reason is written down so the next sweep does not "discover" the saving again. **No ingress** (Discord is outbound-only). Secrets:
  `postgres-url`, `agent-runner-token`, `vultur-discord-token`; env mirrors
  discord-bot's runner wiring (`PERSONA_RUNNER_URL` plain value).
- **`cd.yml`** builds + deploys + startup-health-checks (`persona_gateway_starting`)
  the gateway with the same SHA as the rest, so `persona_gateway/` or `shared/`
  changes can't lag on a hand-pushed tag.

## Diagnosing "sibling persona X no responde" — host first, never the corpus

When a sibling goes silent, the FIRST hypothesis is a dead host, not a code or
corpus bug. In order:

1. **Is its host alive?** The `persona-gateway` Container App running + its
   revision healthy (or, pre-deploy, the local `python -m persona_gateway run`
   process + its env). A sibling has NO Azure Container App of its own unless one
   was stood up — confirm it exists before blaming the corpus/RAG.
2. **Is its env present?** The gateway needs `POSTGRES_URL`,
   `PERSONA_RUNNER_URL`, `PERSONA_RUNNER_TOKEN`, and its
   `<PERSONA>_DISCORD_TOKEN`. Missing any → it crashes at
   `PersonaRuntimeConfig.from_env()` / logs `persona_gateway_no_token` and never
   starts. (The local `.env` historically lacked these — only Insult's
   `DISCORD_TOKEN` was there.)
3. **Does it answer in its OWN voice?** The functional contract is
   `agent_client.chat("", …, persona_id="<id>")` → the runner loads
   `shared/personas/<id>.md` (shipped into the runner image via
   `COPY shared/personas/ /app/personas/`) and answers AS that persona. "Vultur
   responds but sounds like Insult" means the runner is NOT honoring `persona_id`
   — a different bug than silence. Verify the voice, not just that *a* reply
   landed (Art. 2).

A silent sibling is a dead/misconfigured host until a real reply in its own voice
proves otherwise. Do not iterate on the corpus, prompt, or RAG before steps 1-3.

## Why this rule exists

2026-06-16: Bernard reported "vultur no responde en #general cuando se le pide
recomendar pelis." It was not a film-corpus bug — the `persona_gateway` process
was not running AND its prod env was absent from the local `.env`, so Vultur had
no live host and was mute to everything, not just pelis. The fix was to give it
the durable `persona-gateway` Container App home, mirroring `alice-bot`. The
recurring trap is treating a sibling like a code feature when it is really an
ops/host problem — the same lesson Arbor TTS taught for voice.
