# Robustness Rules

> **Post-purga (2026-07-14, 2f8d9ad):** the prefix-command bot
> (`!chat`/`!buscar`/`!memoria`/`!perfil`/`!ping` + their cooldown table) and
> the direct-Anthropic `LLMClient` (`personas/insult/core/llm.py`) are DELETED.
> The live turn path is `persona_gateway/` → `persona_runner` `/v1/turn`. This
> file describes the live failure surfaces plus the historical lessons that
> still bind.

## Error Handling
- The live guarded entry is `persona_gateway/gateway.py::_dispatch`: any turn
  failure logs `persona_gateway_turn_failed` and NEVER exposes internals to the
  channel — the recovery is a neutral "…" send, itself guarded, falling through
  to a reaction (different rate-limit bucket) if the send 429s.
- **The host-routed path (THE path post-cutover) no longer ends in "…" from the
  persona (2026-09-03, v4.38.0).** The host summons with `wait: true`
  (`demux_ai/summon.py::summon_and_wait`), the gateway awaits the turn and
  answers 200 delivered/empty or 502 failed (`dispatch_invite(fallback=False)`
  posts nothing), and `demux_ai/fallback.py` retries ONCE with the same persona
  and then speaks for the house, naming who could not answer. KQL receipts per
  turn: `host_turn_delivered` / `host_turn_failed` / `host_turn_recovered` /
  `host_turn_gave_up` / `host_fallback_posted`. The gateway's own "…" survives
  only where the host is structurally deaf — a DM, a sibling's `[INVITE:]` —
  and for legacy fire-and-forget callers (202). Why: eight ellipses to Alex in
  two days for a server-side budget cut the host never learned about, because
  a 202 at scheduling time made success and failure indistinguishable.
  A retry is safe because a "failed" turn delivered nothing: `turns.py` reports
  delivered the moment the user saw text, and faults after that (store, TTS)
  are logged, never raised.
- NEVER expose "Claude", "Anthropic", "API", or internal error types to users.
- DB write failures are logged but don't kill the turn (the user still gets a
  response).
- Never let exceptions propagate silently — always log with structlog.
- **Fail-safe doctrine (guidance/behavior engine):** any fault in guidance
  assembly degrades to a normal turn, never a mute bot
  (`persona_core/guidance.py`).

## Un turno NUNCA viaja en una sola request — el ingress corta a los 240 s

El ingress de Azure Container Apps cierra cualquier request HTTP a los **240 s**
y no se configura (ni `terminationGracePeriodSeconds` ni ningún timeout del app
lo mueven). Un turno de Opus con caché frío puede tardar más: el **2026-09-19**
uno de Vultur tardó **326.9 s**, AIRE lo entregó completo (`elapsed_ms=326925`,
1,787 tokens, $0.33), y no había nadie escuchando — el gateway cortó su request
al runner a los 240 s (`agent_runner_client_timeout`), el host cortó la suya al
gateway a los 240 s (`summon_rejected 504 stream timeout`) y **reintentó ENCIMA**
del turno vivo (segundo Opus en paralelo). La respuesta existió, se pagó y se tiró.

**La ley:** las dos costuras que cruzan el ingress viajan por **boleto**
(`persona_core/tickets.py`): el trabajo corre en una task del proceso que lo
recibe y el cliente pregunta por él en requests **cortas** (poll ≤ 50 s).

| Costura | Alta | Poll | Presupuesto del turno |
|---|---|---|---|
| gateway → runner | `POST /v1/turn/jobs` → 202 `job_id` | `GET /v1/turn/jobs/{id}?wait_s=` | `first_turn_timeout_s` = 600 s (gateway) |
| host → gateway | `POST /invite` con `wait+ticket` → 202 `turn_id` | `GET /invite/turns/{id}?wait_s=` | `SUMMON_WAIT_BUDGET_S` = 660 s (host, por encima del gateway para que sea el gateway quien declare el fallo) |

- **Ningún read timeout de request puede acercarse a 240 s.** Un número ≥ 240 en
  un `httpx.Timeout` de estas costuras es el bug, aunque "se vea generoso": el
  ingress lo va a cortar antes y el cliente va a leer "unreachable".
- **Un 404 a media espera es reinicio, no rechazo** → `RunnerDownError` /
  `"unreachable"`, para que el reintento único del host aterrice en la réplica
  nueva. Un poll que se cae por red se vuelve a preguntar; el turno sigue vivo.
- El camino síncrono (`POST /v1/turn`, `wait` sin `ticket`) queda solo para un
  rolling update a medias (cliente nuevo, servidor viejo). Cuando ya no haya
  servidores viejos, se borra ([[migrations-end-with-deletion]]).
- `_MUTE_GRACE_SECONDS` (660 s) del `/health` va por encima del presupuesto: un
  turno vivo de 5 minutos no es una persona muda.
- **El alta es idempotente y sobrevive el arranque en frío (2026-09-23, v4.39.6).**
  El runner corre en `min=0`; el ingress acepta la conexión con cero réplicas y
  **retiene el alta durante todo el arranque** (medido: 169 s desde el summon
  hasta que el runner recibió el POST, con el proceso listo a los 86 s). Con un
  read timeout de 60 s el gateway leía `ReadTimeout` → `RunnerDownError`, el host
  reintentaba y se rendía a los ~135 s, y el ingress entregaba DESPUÉS los dos
  POSTs encolados: dos turnos de Opus en frío que nadie leyó, y el host hablando
  por la casa. Por eso el gateway manda un `job_id` propio en el alta
  (`TurnRequest.job_id`) y el runner deduplica por él (`TicketRegistry.submit(…,
  ticket_id=)` → `ticket_reused`); con eso el `ReadTimeout` del alta **sí** se
  reintenta — con el MISMO id — mientras quede reloj del turno
  (`agent_runner_client_submit_retry`), y el read timeout del alta es
  `JOB_SUBMIT_READ_TIMEOUT_S = 200` (cubre el frío, bajo el techo del ingress).
  Un `ReadTimeout` con un id NUEVO por intento volvería a ser el turno doble.

### El boleto es DURABLE en las dos costuras (2026-09-23, v4.40.x)

Un boleto que sólo vive en RAM convierte cada restart a media generación en un
404 y un reintento ciego río arriba: se re-pregunta a AIRE, o —si el gateway ya
había hecho `send_chunked`— sale una **segunda respuesta**. Por eso la misma
clave viaja host→gateway→runner y aterriza en Postgres en los dos saltos que ya
lo tienen (`persona_core/tickets.py` + `invite_turns` en el gateway,
`turn_jobs` en el runner):

- **RAM es la dueña; la fila es el handoff entre procesos.** `TicketRegistry`
  consulta la fila sólo cuando RAM no tiene el boleto: terminada → su resultado;
  viva en otra réplica (latido fresco) → `running`; huérfana → **claim por
  compare-and-swap** (exactamente un ganador) y reanudación bajo el mismo id.
  Lease: latido cada 10 s, vencido a los 60, `MAX_ATTEMPTS=2`, `deadline_at` =
  presupuesto del turno (600 s). Reloj de la base, nunca `time.time()`.
- **El host acuña el `turn_id`** y lo reusa en su reintento SÓLO tras
  `unreachable` (no sabe qué pasó); tras un `failed` declarado acuña otro.
  Outcome `uncertain` = el gateway murió entre `sending` y `delivered`: ni
  reintento ni aviso de la casa — `host_turn_uncertain` en rojo y se para.
- **El gateway reanuda por ETAPA, nunca re-corre el turno:** `accepted →
  runner_done → markers_done → sending → delivered`. Desde `runner_done` no
  vuelve a llamar al runner; desde `markers_done` no repite marcadores; desde
  `sending` NUNCA reenvía. `send_chunked` ya no levanta tras el primer chunk
  enviado (devuelve los que salieron, `partial=true`), y el assistant se guarda
  con `discord_message_id` del primer chunk (idempotente por el índice parcial).
- **El runner reanuda re-preguntando** (fase A): `TurnRequest.resumed` no
  re-pliega la historia y lleva la nota de `prompts_md/turn_resume_note.md`.
  Sólo si el intento anterior CRUZÓ a AIRE (`aire_sent_at`,
  `turn_jobs.crossed_to_aire`, v4.40.23); si murió antes, corre como turno
  nuevo. Así cada `aire_route_turn_resumed` = un mensaje duplicado en AIRE.
  Lo que AIRE vio (`resumed`) y lo que ya está en `messages` (`ask_stored`) son
  ejes distintos: un job `pipeline="runner"` (og118) reanudado nunca vuelve a
  guardar la pregunta, haya cruzado o no, y la reanudación del arranque entra
  por `serve_turn`, la misma puerta que el alta (v4.47.3). Un
  job con adjuntos es no-reanudable (no se persisten) → 502 `not_resumable` →
  el host reintenta con id nuevo. Grace del runner: **600 s**
  (`RUNNER_SHUTDOWN_DRAIN_S=570`, luego suelta las filas para la sucesora).
  Fase B (AIRE `background:true` + reattach) en
  `.claude/backlog/aire-background-turn-reattach.md`.
- **Fail-soft:** cualquier fallo de Postgres degrada al contrato sólo-RAM (404 →
  `unreachable` → reintento del host). Un 404 ya sólo significa "id desconocido
  o Postgres inalcanzable".

Tests que fijan la clase: `tests/shared/test_tickets.py`,
`tests/agent/test_turn_jobs_api.py`, `tests/integration/test_agent_client_turn_jobs.py`,
`tests/core/test_gateway_invite_ticket.py`, `tests/test_summon.py` (bloque boleto);
y para el ledger: `tests/agent/test_turn_ledger_pg.py`, `tests/core/test_invite_turns_pg.py`
(Postgres real: CAS con un solo ganador, cierre/latido sólo del dueño),
`tests/agent/test_runner_shutdown.py`, `tests/core/test_turn_delivery_ledger.py`
(etapas, sin reenvío desde `sending`, envío parcial), `tests/test_invite_turns_repo.py`,
`tests/agent/test_host_fallback.py` (turn_id reusado sólo tras `unreachable`, `uncertain`).

## LLM Resilience (historical lessons — the client died, the doctrine stands)

The tuned retry loop below lived in the deleted `LLMClient`; today the gateway
calls the runner over HTTP (`persona_core/runner/` client) and the runner
owns the model call via the Claude Agent SDK. When (re)building any direct
model client, these remain law:

- **Disable SDK-level retries** (`max_retries=0` on the SDK client) — the outer
  loop owns retry policy. Otherwise the SDK silently retries ~2x internally and
  inflates observed timeouts from 30s to ~90s per attempt.
- RateLimitError / 529 Overloaded: exponential backoff **with jitter**, bounded
  attempts; honor `retry-after` when ≤60s.
- AuthenticationError: fail immediately, no retry.
- Timeout/ConnectionError: cap at 2 attempts total — five timeouts × 30s of
  dead air is too punishing for a chat surface.
- Give the user an in-character signal after the first timeout instead of
  silent dead air.

## Lifecycle (live: `persona_gateway/boot.py` + `gateway.py`)
- **Bind → connect → login order is mandatory**: the health/API port (8788)
  binds BEFORE Postgres connect and Discord login, so the platform's startup
  probe never kills a slow boot (root fix of the ActivationFailed hangs,
  v4.22.14 — see [[reference_activationfailed_gateway_hang]]).
- Each persona runs under its own supervision; one persona crashing logs
  `persona_gateway_persona_failed` without silently killing the siblings, and
  `persona_gateway_all_personas_down` fires when nothing is left.
- `/health` is honest — it reflects real serving state, not an early flag
  (the 2026-06-13 boot-zombie lesson: `is_ready:true` while dead for 14 min).

## Logging
- Use structlog everywhere (never print()).
- Prefer structured event names with a stable prefix (the gateway family is
  `persona_gateway_*`) and typed fields over prose; `LOG_FORMAT=json` in prod
  (ANSI in prod logs broke KQL parsing once — see
  [[feedback_kql_has_lies_and_ansi_logs]]).
- Log every stage transition of a turn so an orphaned turn (start without end)
  is detectable in KQL — see the dropped-messages workflow in `testing.md`.

## Destructive Post-Processing — MANDATORY

> The three files named in the 2026-05-18 table died in 2f8d9ad, but the
> principle binds every LIVE post-LLM mutator: the marker strippers
> (`persona_core/markers.py`, `persona_core/reactions.py::strip_reactions`),
> and the style-profile updater (`persona_core/style.py` — which today
> implements the two-regime stickiness this lesson demanded).

Any post-LLM mutator (regex stripper, heuristic truncator, profile updater)
that acts on a single signal MUST consider context before mutating output
or persistent state. Three production bugs hit users within the same hour
on 2026-05-18 from this exact class (files as they existed then):

| Bug | File (historical) | Symptom |
|---|---|---|
| Echo strip ate quoted citations | `core/character/formatting.py:strip_echoed_quotes` | `"su equipo no crece" — eso te lo inventas` became ` no crece" — eso te lo inventas` (orphan quote + missing opener + missing content) |
| Language flipped on a single paste | `core/style.py:UserStyleProfile.update` | Bernard pasted an English email; bot responded entirely in English next turn |
| Length enforcer truncated 80-90% of content | `core/character/formatting.py:enforce_length_variation` | Cut a 217-word response to 38 words, silently dropping `[REMEMBER:]` and `[REACT:]` markers in the tail |

### Required design when mutating LLM output

- **Quote-adjacency rule** (text mutators): if the matched span is inside
  `"..."`, `'...'`, `«...»`, smart quotes, it is almost certainly
  intentional content — skip the mutation. Use **paragraph-level evidence**
  (`≥2 quote chars in the paragraph → assume intentional citation, skip`).
  Character-adjacent lookbehind/lookahead is NOT enough; quotes may be
  separated from the span by 1-2 words.
- **Marker rescue** (truncators): before dropping any portion of the LLM
  output, extract `[REMEMBER:]` and `[REACT:]` markers from the dropped
  region and re-append to what remains. The persistence and reaction
  layers must not silently lose state because of a formatting heuristic.
- **Two-regime stickiness** (profile updaters): brand-new profiles
  (`count < CONFIDENCE_THRESHOLD`) may flip on a single signal — they are
  still learning. Confident profiles MUST require N consecutive
  other-side signals (streak counter) before flipping a discrete field
  like `detected_language`. Continuous fields keep using EMA. Live
  implementation: `persona_core/style.py` (`lang_switch_streak`).

### Required tests for any new mutator

Every mutator MUST land with at least two tests:

1. The positive case it exists to fix (the bug it claims to detect)
2. The **resistance case** — a near-miss that looks like the target but is
   intentional and must be preserved.

Live examples: `tests/core/test_style.py` (confident profile resists a single
off-language message ⇆ switches after consecutive ones).

Without the resistance test, the mutator's regression risk is invisible
until production hits the wrong shape.

### Code-review checklist before approving a new mutator

- What context would make this mutation wrong? (quote-wrapped span,
  established profile, marker-bearing tail)
- Is there a paragraph-level / multi-signal check before the hard
  mutation, or does it act on the first match?
- Are there tests for both the positive case AND the resistance case?
- Does the telemetry event include a `reason` field describing WHY the
  mutation fired?

Reference: full case studies in
`memory/feedback_destructive_post_processing.md`.
