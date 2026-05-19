"""Mexico City wall-clock context injected into the system prompt.

Centralized so chat, voice, tools, and the prompt builder all see the same
instant for a given turn. Computed fresh per-call — no caching — because the
result lands in a non-cacheable region of the prompt anyway.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def _get_current_time_context() -> str:
    """Build a human-readable current time string for the system prompt (Mexico City timezone)."""
    now = datetime.now(ZoneInfo("America/Mexico_City"))
    day_names_es = {0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"}
    month_names_es = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    day_name = day_names_es[now.weekday()]
    month_name = month_names_es[now.month]
    hour = now.hour
    if 5 <= hour < 12:
        period = "mañana"
    elif 12 <= hour < 19:
        period = "tarde"
    elif 19 <= hour < 24:
        period = "noche"
    else:
        period = "madrugada"
    return f"{day_name} {now.day} de {month_name} {now.year}, {now.strftime('%H:%M')} ({period})"
