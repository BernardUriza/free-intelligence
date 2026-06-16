"""Host degrader — gpt-4.1 honest operational degradation text.

PR-4b slice 3. The demux host's gpt-4.1 brain (``HostRouterLLM``, slice 1) has
two operational jobs per the north-star ADR: ROUTE (classify intent / pick a
persona) and DEGRADE (produce an honest operational notice when NO persona can
serve the turn). This module owns the DEGRADE job.

It runs ONLY at the tail of a failed turn — after every persona path is
exhausted (the runner is down AND a real sibling-persona failover was not
possible). It never touches the happy path and never serves AS a persona: the
text it produces is a neutral, honest "I can't take this turn right now" notice,
NOT Insult / ALICE / Vultur impersonated. The deliberate provider split (OpenAI
host vs Claude personas) is what lets the host still say something honest when
the whole Claude runner is down.

Wiring is INERT by default (slice 3): the persona pipeline only builds + calls a
degrader when ``host_router_enabled`` is True (see
``personas.insult.composition.build_host_degrader_port``). With the flag off —
prod's default — this module is never imported, gpt-4.1 is never called, and the
honest-degradation path stays exactly the static in-character notice it has
always been. Flipping the flag live (real gpt-4.1 spend) is a separate, gated
act.

Boundary: ``demux_ai`` must never import ``personas.*`` (host→persona ratchet is
0). This module imports only the host's own ``host_llm`` + structlog.
"""

from __future__ import annotations

import structlog

from demux_ai.host_llm import HostRouterError, HostRouterLLM

log = structlog.get_logger()

# The host degrader's operational directive. NOT a persona prompt: it must
# produce a neutral, honest "can't serve this turn" notice — never impersonate a
# character, never expose the underlying tech (no "AI" / model names), brief, in
# the user's language. The host has no character to keep in, so the full
# instruction is passed per call (slice 1 contract).
_DEGRADE_INSTRUCTION = (
    "Eres el recepcionista operativo de un sistema de personas conversacionales. "
    "Ninguna persona pudo atender este turno (su motor está caído). Escribe UN "
    "aviso breve, honesto y neutral de que ahora mismo no se puede responder y que "
    "lo intente de nuevo en un momento. Reglas duras: NO te hagas pasar por ningún "
    "personaje ni imites un tono de personaje; NO menciones tecnología, modelos, "
    "IA, ni nombres de proveedor; responde en el idioma del usuario; máximo dos "
    "frases; sin disculpas serviles."
)


class HostDegrader:
    """Produces honest operational degradation text via the gpt-4.1 host router.

    Thin wrapper over ``HostRouterLLM``: one call, one short notice. A host-router
    failure surfaces as ``HostRouterError`` (the slice-2 taxonomy's
    ``ROUTER_ERROR``) so the caller can log it distinctly and fall back to its own
    conservative static notice — the degrader never swallows its own failure into
    a fake-green string.
    """

    def __init__(self, router: HostRouterLLM | None = None):
        self._router = router or HostRouterLLM()

    async def degrade(self, *, reason: str, user_text: str) -> str:
        """Return one honest operational degradation notice.

        ``reason`` is the upstream ``FailoverReason`` value (why no persona
        served — e.g. ``runner_down``); it is logged for observability, not shown
        to the user. ``user_text`` is the last user message so the notice can
        match the user's language. Raises ``HostRouterError`` if the host router
        itself fails — the caller owns the conservative fallback."""
        log.info("host_degrade_start", reason=reason, user_text_len=len(user_text))
        result = await self._router.complete(_DEGRADE_INSTRUCTION, user_text)
        text = result.text.strip()
        log.info(
            "host_degrade_complete",
            reason=reason,
            model=result.model,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            text_len=len(text),
        )
        return text


__all__ = ["HostDegrader", "HostRouterError"]
