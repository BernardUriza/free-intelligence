"""Operator-tunable config for the persona gateway.

The cadences, timeouts, batch sizes and window limits that an operator might
reasonably tune under prod load live HERE, as a single `pydantic-settings`
`BaseSettings` (the repo's canonical config convention — same family as
`persona_core.persona.config.PersonaRuntimeConfig` and Insult's `Settings`).
Reading them through env-typed fields beats a scatter of `os.environ.get`
casts that silently mis-parse.

What is DELIBERATELY NOT here (it stays a code constant in `gateway.py`): values
that encode a fixed external contract, not a knob — Discord's 1990/2000 char cap,
the bind-poll interval, the 🔊 emoji. The rule: if an operator would plausibly
change it in prod without a code review, it's config; if it encodes an external
protocol invariant, it stays a constant.

`CONFIG` is instantiated once at import (all fields have defaults, so it is safe
at module top-level even with no env — CI included). The `@tasks.loop` decorators
read their interval off this instance at class-definition time, so env overrides
must be present before import (always true in prod).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings

from persona_core.tts import DEFAULT_SUSURRO_URL


class GatewayConfig(BaseSettings):
    """Env-overridable operational knobs. Field name X ← env var `X` (case-insensitive)."""

    # Durable research jobs: drain cadence, the generous read timeout a deep
    # research turn gets (WebSearch + long reasoning — the job IS the heavy case,
    # not the interactive 120s default), retry ceiling, and per-tick batch size.
    research_drain_seconds: float = 45.0
    research_timeout_s: float = 360.0
    research_max_retries: int = 2
    research_batch: int = 2

    # Standing agendas: how often each persona wakes to see what's due (the
    # per-agenda `cadence_hours` throttles real frequency, not this interval).
    agenda_check_seconds: float = 600.0
    agenda_timeout_s: float = 360.0
    agenda_batch: int = 2
    # An agenda speaks unprompted, so it only speaks during waking hours (CDMX).
    # Without this a 24h cadence that first came due at 03:00 posts at 03:00
    # forever — which is how Vultur woke Bernard two nights running.
    agenda_daytime_start: int = 9
    agenda_daytime_end: int = 22

    # Self-reflection (slice 4): the loop wakes every 6h but the DURABLE gate in
    # `agents.last_reflected_at` only lets a pass run weekly per persona; a pass
    # needs enough lived turns to be worth judging, and writes at most N facts.
    reflection_check_seconds: float = 21600.0
    reflection_min_interval_s: float = 604800.0
    reflection_window: int = 40
    reflection_min_turns: int = 12
    reflection_max_facts: int = 3
    # First tick waits out the deploy window: gateway + runner ship in the same
    # CD wave, so a tick at boot stampedes a runner that is still cycling (the
    # 2026-07-16 first-pass 503s). 15 min = runner warm, deploy settled.
    reflection_boot_warmup_s: float = 900.0

    # Reminders: 30s keeps "recuérdamelo a las 8" honest to the minute; a reminder
    # more than MAX_LATENESS late is retired unsent (nobody wants yesterday's 3am).
    reminder_check_seconds: float = 30.0
    reminder_timeout_s: float = 90.0
    reminder_max_lateness_s: float = 86400.0

    # How many prior channel messages to replay to the runner, and how much of the
    # channel tail the automatic fact extractor reads (matches the legacy backstop's
    # 10-message window with headroom for the current turn).
    recent_limit: int = 30
    facts_recent_window: int = 12

    # Keyword-relevant OLDER turns merged in alongside `recent_limit`, so a
    # persona can reach past the 30-message window instead of forgetting
    # everything older (the pre-purge "recent + relevant" retrieval).
    relevant_limit: int = 5

    # Automatic fact extraction model (the source='auto' backstop). None → the
    # runner picks its own judge default (Haiku class).
    facts_extraction_model: str | None = None

    # El presupuesto del TURNO, no de una request: el ingress de Container Apps
    # corta toda request a los 240 s, así que el turno viaja por boleto
    # (`/v1/turn/jobs` + poll) y este reloj lo lleva el cliente. 600 s con
    # receipt: 2026-09-19 un turno de Vultur tardó 326.9 s, AIRE lo entregó
    # completo y el corte a 240 s lo tiró.
    first_turn_timeout_s: float = 600.0

    # Cutover switch (#6): when the omnipresent host (demux_ai) owns reception, the
    # gateway personas go INVITE-ONLY — they stop self-answering their own @mentions
    # and respond ONLY to the host's /invite. Without this, a mention makes a persona
    # answer twice (once via its own mention-gate, once via the host's route+invite):
    # the "ventana de dos bots peleando". Flip to True on the gateway env at the SAME
    # time the host goes live (HOST_DISCORD_TOKEN set). Default False = pre-cutover.
    host_owns_reception: bool = False

    # Drenaje al recibir SIGTERM: cuánto se le da a los turnos EN VUELO para
    # aterrizar antes de cerrar igual. Tiene que ser MENOR que el
    # `terminationGracePeriodSeconds` del Container App — si no, la plataforma
    # manda SIGKILL a media espera y el drenaje no compra nada. Hoy el grace es
    # `null` en las tres apps (el default de la plataforma), así que 25s es un
    # techo conservador; subirlo va junto con el grace, nunca antes.
    drain_timeout_s: float = 25.0

    # Voice (susurro TTS). Auto-speak replies at/above N chars (0 = manual 🔊 only).
    auto_tts_min_chars: int = 0
    susurro_url: str = DEFAULT_SUSURRO_URL
    susurro_key: str = ""

    model_config = {"env_file": None, "extra": "ignore"}


CONFIG = GatewayConfig()
