# Cross-turn durable research jobs — "@mention → ack now → post the deep answer back later"

Status: Proposed
Proposed: 2026-07-05 by Bernard (surgió de og118: el persona prometía trabajo en background que su runtime stateless no podía cumplir → guard de honestidad ahí; el escenario async-real ENCAJA aquí, no en og118)

## What it is

Un usuario @menciona al bot con una tarea pesada de investigación/análisis
(multi-step, minutos). El bot **acusa recibo de inmediato** ("va, te lo armo,
te aviso aquí"), un **worker durable** corre el job multi-step a lo largo del
tiempo, y **postea el resultado de vuelta al canal cuando termina** — desacoplado
del turno que lo originó. En Discord esto NO es una mentira (como sí lo sería en
og118, chat en vivo con el usuario mirando el stream): el canal es async-nativo,
el "te aviso" es el modelo de interacción natural.

Por qué discord-bot es el hogar correcto (las 5 piezas que og118 no tiene):
- **Async-nativo** — `discord.py`, entrega diferida al canal desde un background
  loop ya es battle-tested (reminders, proactive).
- **Stateful** — Postgres/pgvector en Azure compartida; una tabla de jobs no rompe
  ningún invariante de statelessness (og118 sí lo rompería).
- **Transcript durable** — tabla `messages` (`khimeras_shared/memory/postgres_schema.sql:57`).
- **Scheduler-shape ya en prod** — la tabla `reminders` + su drain loop.
- **Precedente de worker pesado separado** — el Container App Job `fact-consolidation`.

## Canonical path to reuse (Art. 6) — extender, NO reinventar

El subsistema `reminders` YA ES el molde del job durable, en producción:
- Tabla `reminders` (`postgres_schema.sql:138`) + `RemindersRepository`
  (`khimeras_shared/memory/repositories/reminders.py`): `save` RETURNING id,
  `get_pending(now)` (`delivered=0 AND remind_at<=now`), `mark_delivered`, retry/ack.
- Drain loop `personas/insult/tasks/reminders.py:32-140`:
  `@tasks.loop(seconds=30)` → `get_pending` → `channel.send` de vuelta →
  `mark_delivered`, con crash-survivability (las filas persisten, el loop re-lee
  al restart) y un ack/retry sweep `@tasks.loop(seconds=300)`.
- Motor LLM: el `persona-runner` FastAPI, `POST /v1/turn` (multi-step, Claude Agent
  SDK, `personas/insult/agent/runner.py:737`) para el trabajo pesado; `/v1/judge`
  para one-shots. NO se toca fi_runner.

Slice canónico (mirrors `reminders.py`, cero infra nueva):
1. Tabla nueva `research_jobs(id, channel_id, user_id, prompt, status, result,
   retry_count, created_at, delivered_at)` en `postgres_schema.sql` (idempotente
   `CREATE TABLE IF NOT EXISTS`, junto a `reminders`/`siesta_state`). Join natural
   por `channel_id`/`user_id` (TEXT Discord IDs) a `messages`/`principal_facts`.
2. `ResearchJobsRepository` clon de `RemindersRepository`.
3. En el handler del @mention: `INSERT` de un row `queued` + `channel.send` del ack
   inmediato (NO await del turno pesado).
4. Un `@tasks.loop` nuevo en `personas/insult/tasks/` que drena `queued`, llama al
   runner `/v1/turn`, `channel.send` el resultado, marca `done`. Hereda crash-survival
   y el retry sweep gratis.

Detalle a resolver: `/v1/turn` mantiene un `ClaudeSDKClient` pooled por canal — el
job debe correr con una sesión propia (o `/v1/judge` con un prompt multi-step
armado) para no ensuciar el hilo interactivo del canal. Respetar el mismo
`ToolPolicy` + corpus binding que un turno vivo (el worker NO es un path de más
privilegio).

## Framework note (fi-runner) — resumable plan is a FUTURE extract, not now

Assessed 2026-07-05 (verified against fi-runner source). fi-runner does NOT need
prep for slice 1 — what this feature needs is already there:
- multi-step agentic turn → `Runner.run_stream`, exposed as `/v1/turn`;
- session isolation for the job → pass a distinct `session_id` (`runner.py:171,199`),
  so the job never pollutes the channel's interactive thread;
- tool policy + corpus binding → already applied per turn.

The ONE genuine framework gap: the `task_tracker` plan/step state is **in-turn
only** — `_PlanStreamObserver` (`runner.py:464`) derives stream events but nothing
persists the plan; `conversation_store` saves the user/assistant *exchange* for
replay, NOT the plan progress. There is NO durable-job / resumable-turn primitive
in fi-runner (the "background" hits there are observability narration, not jobs).
So a long job that crashes mid-plan loses its progress.

Do NOT build a resumable-plan primitive in fi-runner now — that would abstract from
one unbuilt consumer (premature abstraction, exactly what framework-first-canary
forbids). Slice 1 gets crash-robustness for free from the `reminders` pattern:
the row persists, the loop re-reads on restart, re-calls `/v1/turn` **from the
top**. A job that re-runs whole and eventually posts a valid result is fine for v1
(costs one retry of tokens). ONLY if re-run-from-top proves too expensive (very
long jobs, many steps wasted per retry) does a **persistent/resumable task_tracker
plan** earn its place as a fi-runner primitive — extracted THEN, with this canary
proving the need, not before.

## The decision that's the owner's

Si se construye y cuándo — es un feature real en un bot de prod multi-guild.
El primer slice (tabla + repo + drain loop + ack) es un arranque deliberado con
GO per-level de Bernard, secuenciado contra los otros items en vuelo (cross-talk
@frugi, el move de `persona_runner/`, el rename del gateway). No urgente; captura
para no perder el análisis.

## Status / next step

No construido. La feasibility está verificada a fondo (topología de 4 contenedores,
`reminders` como molde, Postgres compartida). Unblock = GO de Bernard para el
primer slice. Relacionado: [[persona-runner-package-move]] (el runner que el job
llamaría), y el guard de honestidad de og118 (free-intelligence PR #314) que es el
lado opuesto de este mismo tema.
