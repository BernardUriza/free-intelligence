"""Cuándo una persona puede hablar sin que nadie le haya hablado.

Núcleo de decisión de la proactividad, persona-agnóstico y sin Discord: dice
CUÁNDO es lícito arrancar una conversación, no quién la arranca ni qué dice.

Portado (no reescrito — Art. 6) de `personas/insult/core/proactive.py`, que la
purga `2f8d9ad` borró el 2026-07-14 junto con sus 481 líneas de tests, sin
replantarlo. Con él murió lo que Bernard extrañaba: *"antes Insult de vez en
cuando saltaba a preguntarnos cómo estábamos"*. El original es suyo, `b86a79b`
(2026-04-01). Ver `.claude/backlog/proactividad-muerta-restaurar-en-el-host.md`.

Sigue vigente el modelo del original (patrón Nomi AI):
  - 3 estados de actividad, para no interrumpir una conversación viva
  - backoff exponencial sobre proactivos no contestados
  - horas de silencio

Dos cambios respecto al original, ambos deliberados:
  1. **Vive en `persona_core/`**, no dentro de una persona. El dueño de la
     iniciativa ahora es el host, que despierta a la persona que toque — la
     decisión de CUÁNDO no puede pertenecer a ninguna de ellas.
  2. **Reloj inyectable** (`now`), como `demux_ai/batch.py`, que es el patrón que
     este repo ya declara canónico para lógica pura con tiempo. El original
     llamaba `datetime.now()` adentro y volvía los tests dependientes del reloj
     de la máquina.
"""

from __future__ import annotations

import random
import time
from enum import Enum

import structlog

log = structlog.get_logger()


class ConversationState(Enum):
    """Qué tan viva está la conversación de un canal."""

    ACTIVE = "active"  # alguien habló hace poco — NO interrumpir
    COOLING_DOWN = "cooling_down"  # acaba de terminar — dejarla asentarse
    IDLE = "idle"  # es lícito arrancar


ACTIVE_THRESHOLD = 15 * 60
COOLING_THRESHOLD = 2 * 3600

BASE_INTERVAL_HOURS = 2.0
MAX_INTERVAL_HOURS = 24.0

QUIET_HOURS = range(3, 7)
SEND_PROBABILITY = 0.4
WORLD_SCAN_PROBABILITY = 0.3


def get_conversation_state(last_user_message_ts: float | None, now: float | None = None) -> ConversationState:
    """Estado del canal según cuándo habló un humano por última vez.

    Sin mensajes previos el canal está IDLE: un canal en el que nadie ha hablado
    nunca no tiene conversación que interrumpir.
    """
    if last_user_message_ts is None:
        return ConversationState.IDLE
    elapsed = (time.time() if now is None else now) - last_user_message_ts
    if elapsed < ACTIVE_THRESHOLD:
        return ConversationState.ACTIVE
    if elapsed < COOLING_THRESHOLD:
        return ConversationState.COOLING_DOWN
    return ConversationState.IDLE


def compute_backoff_interval(unanswered_count: int) -> float:
    """Horas de espera mínima según cuántos proactivos seguidos nadie contestó.

    Cada proactivo ignorado DUPLICA la espera: 2h → 4h → 8h → 16h → 24h (tope).
    Se reinicia cuando un humano contesta después de un proactivo.

    Esta función es la que hace que la proactividad sea compañía y no plaga, y
    pesa más ahora que antes: con cinco personas rotando, sin backoff serían
    cinco bots hablándole solos a un canal que ya no responde.
    """
    interval = BASE_INTERVAL_HOURS * (2 ** max(0, unanswered_count))
    return min(interval, MAX_INTERVAL_HOURS)


def should_send_now(
    hour: int,
    last_proactive_ts: float | None,
    last_user_message_ts: float | None,
    unanswered_count: int = 0,
    now: float | None = None,
    roll: float | None = None,
) -> bool:
    """¿Es lícito arrancar una conversación en este canal, ahora?

    En orden: horas de silencio → estado del canal → backoff → probabilidad.
    Cada compuerta puede vetar sola; ninguna puede forzar el envío.

    `roll` inyecta el dado (0.0-1.0) para poder testear la rama probabilística
    sin parchear `random`.
    """
    if hour in QUIET_HOURS:
        return False

    state = get_conversation_state(last_user_message_ts, now)
    if state is not ConversationState.IDLE:
        log.debug("proactive_suppressed", reason=state.value)
        return False

    if last_proactive_ts is not None:
        elapsed_hours = ((time.time() if now is None else now) - last_proactive_ts) / 3600
        if elapsed_hours < compute_backoff_interval(unanswered_count):
            return False

    return (random.random() if roll is None else roll) < SEND_PROBABILITY


def should_world_scan(roll: float | None = None) -> bool:
    """¿Este arranque es una investigación en vez de un saludo?

    El ~30% que sale a buscar al mundo en vez de preguntar cómo estás. Es la
    mitad que Bernard más extrañaba: *"eran investigaciones reales… iba
    acumulando de a poquito hasta que venía y nos contaba"*.
    """
    return (random.random() if roll is None else roll) < WORLD_SCAN_PROBABILITY
