"""El tap del stream de AIRE: la misma corrida que `AIREBackend.run_turn`, con
una llamada por cada `tool_call` en el instante en que pasa.

fi-runner 0.23 llega desde conda (`environment.yml`), no desde el monorepo, y
su `run_turn` drena `run_turn_stream` sin avisarle a nadie. Hasta que una
fi-runner publicada traiga un `on_event`, el drenado con tap vive aquí y copia
su único matiz: el `budget_exhausted` que AIRE emite DESPUÉS del `result` no
tira una respuesta ya en mano (aire #23); sin texto, sigue siendo error.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from fi_runner import AIREBackend
from fi_runner.backend import BackendError, TurnResult
from fi_runner.backends.aire import AIREDoorError

__all__ = ["run_turn_tapped", "wire_tool_call"]

log = structlog.get_logger()


def wire_tool_call(event: dict[str, Any]) -> dict[str, Any]:
    """El frame `tool_call` del contrato, sin el `input` de la herramienta: la
    bitácora dice QUÉ hace el agente, no con qué datos (puede llevar PHI)."""
    tool = event.get("tool")
    return {
        "type": "tool_call",
        "tool": {
            "name": getattr(tool, "name", "") or "",
            "id": getattr(tool, "id", None),
            "server": getattr(tool, "server", None),
            "is_error": getattr(tool, "is_error", None),
        },
    }


async def run_turn_tapped(
    backend: AIREBackend, *, on_event: Callable[[dict[str, Any]], None], **kwargs: Any
) -> TurnResult:
    result: TurnResult | None = None
    try:
        async for event in backend.run_turn_stream(**kwargs):
            kind = event.get("type")
            if kind == "tool_call":
                on_event(event)
            elif kind == "result":
                result = event["result"]
    except AIREDoorError as exc:
        if exc.code != "budget_exhausted" or result is None or not result.text:
            raise
        log.warning("aire_route_budget_cut_after_result", text_len=len(result.text))
    if result is None:
        raise BackendError("AIRE door closed the stream with no result event.")
    return result
