"""El worker de OG118-BACKGROUND-1: `python -m background_worker` dentro del ACA Job.

Misma imagen, mismo share, mismo runner que un turno en vivo. Drena la cola:
reclama el job pendiente más viejo, corre UN turno de fi-runner con la
conversación como historial y la meta como mensaje, y deja el resultado como un
mensaje de asistente en el record (`ConversationStore.append_message`). Termina
cuando no queda nada pendiente — el Job cobra por ejecución, no por réplica.

La persona es la MISMA del chat a propósito: la casita de AIRE se inicializa con
el system prompt, y un prompt distinto reescribiría la base de esa casita
(OG118-LIVING-CLAUDE). Lo que distingue al worker es el mensaje del turno
(`prompts/background_worker_turn.md`), no la identidad.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

from fi_runner import load_prompt

from app import _turn_context, get_conversation_store, get_project_registry
from mcp_background import get_job_store
from runner import AIRE_CHAT_PROJECT, aire_project_for_chat, build_runner

log = logging.getLogger("og118.background_worker")
WORKER_TURN_PATH = Path(__file__).parent / "prompts" / "background_worker_turn.md"
MAX_HISTORY_MESSAGES = 60


def _historial(record: dict) -> list[dict[str, str]]:
    turnos = [
        {"role": m["role"], "content": m["content"]}
        for m in record.get("messages") or []
        if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()
    ]
    return turnos[-MAX_HISTORY_MESSAGES:]


async def procesar(job: dict, runner: Any, conversations: Any, registry: Any) -> str:
    """Corre el job y entrega. Levanta si la conversación ya no existe."""
    owner, cid = job["owner"], job["conversationId"]
    record = conversations.get(owner, cid)
    if record is None:
        raise RuntimeError("la conversación ya no existe")
    AIRE_CHAT_PROJECT.set(aire_project_for_chat(cid))
    prompt = load_prompt(WORKER_TURN_PATH).replace("{goal}", job["goal"])
    result = await runner.run(
        prompt,
        session_id=cid,
        history=_historial(record),
        context=_turn_context(job.get("corpusId"), registry),
    )
    texto = (getattr(result, "answer", "") or result.text or "").strip()
    if not texto:
        raise RuntimeError("el turno terminó sin texto")
    mensaje = {
        "role": "assistant",
        "content": texto,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    }
    if conversations.append_message(owner, cid, mensaje) is None:
        raise RuntimeError("la conversación se borró mientras corría el job")
    return texto


async def drenar(runner: Any | None = None) -> int:
    jobs = get_job_store()
    conversations = get_conversation_store()
    registry = get_project_registry()
    runner = runner or build_runner()
    hechos = 0
    while (job := jobs.claim_next()) is not None:
        log.info("job_start id=%s conversation=%s", job["id"], job["conversationId"])
        try:
            texto = await procesar(job, runner, conversations, registry)
        except Exception as exc:
            jobs.fail(job, str(exc))
            log.exception("job_failed id=%s", job["id"])
            continue
        jobs.finish(job, texto)
        hechos += 1
        log.info("job_done id=%s chars=%d", job["id"], len(texto))
    return hechos


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(name)s %(message)s")
    hechos = asyncio.run(drenar())
    log.info("worker_exit jobs_done=%d", hechos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
