"""og118 Runner — fi-runner built inline, Claude Code backend via OAuth.

Same proven pattern as insult_ai (production): a `Runner` composed inline with
`ClaudeCodeBackend` authed by the ambient `CLAUDE_CODE_OAUTH_TOKEN` (Max
subscription OAuth). v0 is a plain conversational turn — no fi-core capabilities
wired, built-in mutating tools disallowed for safety. The agentic stream
(turn_flow / ToolCall) is emitted natively by `run_stream`; the frontend hook
maps it onto core's contracts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fi_runner import (
    COMPANION_BLOCKED_BUILTINS,
    ClaudeCodeBackend,
    MCPServerSpec,
    Runner,
    ToolPolicy,
    active_corpus_binding,
    load_prompt,
)

# La persona base es CONFIGURABLE por entorno para que un segundo consumer
# (apps/fenix) corra este mismo runtime con su propia voz, sin duplicar el
# servidor: "1 build → N consumers". Sin la variable, la ruta es exactamente la
# de antes, así que og118 no cambia en nada. El prompt sigue viviendo en un .md
# que se lee en runtime (P0 prompts-as-content), nunca inline en el código.
PERSONA_PATH = Path(os.environ.get("FI_PERSONA_PATH") or (Path(__file__).parent / "prompts" / "persona.md"))
COMPANION_CONSTRAINTS_PATH = Path(__file__).parent / "prompts" / "companion_constraints.md"


def _extra_mcp_desde_entorno() -> list[MCPServerSpec]:
    """MCP servers extra declarados por el consumer vía `FI_EXTRA_MCP`.

    Permite que una app construida sobre este runtime (apps/fenix) sume su
    propia herramienta sin que og118 la conozca ni la importe. Sin la variable
    la lista es vacía y og118 se comporta exactamente igual que antes.

    Formato: ``nombre:/ruta/modulo.py`` separados por coma. El módulo se corre
    como ``python -m`` desde su propio directorio, igual que las capabilities de
    fi-core — no se inventa un transporte nuevo.
    """
    crudo = os.getenv("FI_EXTRA_MCP", "").strip()
    if not crudo:
        return []
    specs: list[MCPServerSpec] = []
    for entrada in crudo.split(","):
        if ":" not in entrada:
            continue
        nombre, ruta = entrada.split(":", 1)
        modulo = Path(ruta.strip())
        if not modulo.exists():
            continue
        specs.append(
            MCPServerSpec(
                name=nombre.strip(),
                command=sys.executable,
                args=[str(modulo)],
                # El servidor necesita FENIX_EXPEDIENTES_PATH del entorno padre.
                env_passthrough=True,
            )
        )
    return specs


# Lo que og118 le da a un turno normal. Nombrado porque ahora hay un consumer
# que necesita MENOS: la persona decide lo que el modelo QUIERE hacer, las
# capabilities lo que PUEDE. Cambiar sólo la primera no acota nada.
CAPACIDADES_POR_DEFECTO = ["task_tracker", "rag_store"]

# Los ÚNICOS builtins de Claude Code que este runtime expone al modelo. En el
# SDK, `allowed_tools` gobierna el PERMISO (cuáles corren sin preguntar) y
# `tools` gobierna la DISPONIBILIDAD (cuáles existen en el contexto del modelo).
# Sin setear `tools`, el modelo recibe el preset COMPLETO de Claude Code menos el
# denylist de `ToolPolicy.companion()` — y un denylist es una foto: la tool con
# forma de shell que el preset gane mañana entra sola y en silencio, dentro de un
# contenedor con ingress público que carga CLAUDE_CODE_OAUTH_TOKEN,
# OG118_ACCESS_TOKEN y las llaves de TTS/STT en el env. En discord-bot (misma
# forma de bug, sin denylist) un turno real de producción llamó `Bash` 5 veces.
#
# WebSearch/WebFetch se quedan porque son load-bearing: el tutor del cibercafé
# (apps/fenix, prompts/tutor.md «CUANDO BUSCAS EN INTERNET») corre este mismo
# build_runner con capabilities=["task_tracker"] y su búsqueda de datos reales
# sólo puede venir de estos builtins. Para og118 base y el mostrador de fenix la
# prohibición de internet es de persona (prompt), no de capability — recortarles
# el builtin rompería al tutor, que comparte el runtime.
BUILTINS_DISPONIBLES = ("WebSearch", "WebFetch")


def _verificar_superficie_acotada(options: Any) -> None:
    """Revienta FUERTE si la superficie de capacidad quedó sin acotar.

    Dos direcciones, porque fallan al revés: un allowlist olvida lo que nunca
    nombró; un denylist olvida lo que todavía no existía. `tools=None` significa
    el preset entero — nunca puede salir de aquí así."""
    disponibles = getattr(options, "tools", None)
    if not isinstance(disponibles, list):
        raise RuntimeError(
            "El runner dejó `tools` sin setear: el modelo recibe el preset completo "
            "de Claude Code (Bash, Write, Edit incluidos) dentro del contenedor que "
            "carga el token OAuth y las llaves del env. `allowed_tools` gobierna el "
            "permiso, no la disponibilidad — setea `tools` a una lista explícita."
        )
    coladas = sorted(set(disponibles) & set(COMPANION_BLOCKED_BUILTINS))
    if coladas:
        raise RuntimeError(
            f"El runner expone builtins prohibidos {coladas} a una superficie cuyo "
            f"input es lo que cualquiera escriba en el chat (tools={sorted(disponibles)})"
        )


class BackendAcotado(ClaudeCodeBackend):
    """ClaudeCodeBackend cuya superficie de builtins está ACOTADA por lista.

    fi_runner nunca setea `ClaudeAgentOptions.tools`, así que cualquier consumidor
    suyo hereda el preset completo por default. Este subclass es la costura
    documentada (`build_options` — "the seam a consumer can call"): fija la
    disponibilidad a `BUILTINS_DISPONIBLES` y verifica en cada construcción, para
    que la garantía no dependa de que nadie toque el default del framework."""

    def build_options(self, **kwargs: Any) -> Any:
        options = super().build_options(**kwargs)
        options.tools = list(BUILTINS_DISPONIBLES)
        _verificar_superficie_acotada(options)
        return options


def build_runner(
    persona_path: Path = PERSONA_PATH,
    persona_text: str | None = None,
    session_store: Any | None = None,
    capabilities: list[str] | None = None,
    extra_mcp_servers: list[MCPServerSpec] | None = None,
) -> Runner:
    """Compose the og118 Runner — AGENTIC (step 4): the task_tracker MCP lets the
    agent declare a plan + walk steps, so fi-runner emits plan/step_*/tool_call
    events (the glass-box stream og118's AgentHook maps onto core's
    AgentStreamEvent). Auth is ambient (`CLAUDE_CODE_OAUTH_TOKEN`).

    The system prompt comes from `persona_text` when given (PERSONA-SSOT-1: an
    "elemento" composes the shared fi-personas core + its operative-context block,
    so the persona is NOT a per-repo copy); otherwise it is loaded from
    `persona_path` (the default is the base og118 companion). Everything else —
    capabilities, the corpus binding, the COMPANION tool policy — is identical
    across elements, so a persona swap never widens the filesystem guarantee.

    Whatever the persona is (base or a composed element), the shared og118
    companion PLATFORM CONSTRAINTS are appended here — the single funnel both
    paths pass through — so every element inherits them from ONE source without
    copying the rule per persona or leaking it into the cross-repo fi-personas
    core. Chief among them: the runtime is stateless, so the persona must never
    promise background/async work it cannot do."""
    base_persona = persona_text if persona_text is not None else load_prompt(persona_path)
    model = os.getenv("OG118_MODEL", "claude-sonnet-4-5")
    return Runner(
        # session_store (og118-session-store wiring): the SDK's native durable
        # memory, INJECTED by app.py's lifespan when OG118_SESSION_STORE_DSN is
        # set (Postgres). With it, the Runner prefers resume= over re-folding the
        # client's history replay — the transcript (tool_use/tool_result included)
        # survives a recycled container and the per-turn re-send disappears.
        # None (the default, and today's deploy) keeps the turn byte-identical:
        # client history replay stays the continuity.
        backend=BackendAcotado(default_model=model, session_store=session_store),
        # The Runner must KNOW the model, not just the backend: it is the Runner
        # that stamps the answer's provenance (TurnResult.model → the "powered by"
        # chip). Configured only on the backend, `Runner.model` stayed None and the
        # local route shipped answers that could not say what produced them — while
        # the external-engine route, which reports its own model, could.
        # `chosen_model = model or self.default_model` in the backend, so naming it
        # here changes WHO KNOWS the model, never WHICH model runs.
        model=model,
        persona=f"{base_persona}\n\n{load_prompt(COMPANION_CONSTRAINTS_PATH)}",
        # task_tracker → plan/step glass-box events. rag_store → the agent can
        # ingest/search a project corpus (the Projects-for-the-papelería canary);
        # backend + path resolve from FI_RAG_BACKEND / FI_RAG_STORE_PATH, hdf5 +
        # hashing zero-model embedder by default (no LLM, no network for retrieval).
        # Un runner de MENOS privilegio se pide aquí, no se insinúa en el prompt.
        # `rag_store` expone ingest/delete_document/delete_corpus sobre el corpus
        # del negocio, y `active_corpus_binding` es un addendum al prompt, no una
        # frontera: instruye al modelo a usar un corpus, no le impide tocar otro.
        # Una superficie pública que herede la lista completa puede leerla,
        # envenenarla o borrarla.
        capabilities=CAPACIDADES_POR_DEFECTO if capabilities is None else list(capabilities),
        # proj-corpusbind consumer wiring: when /chat/stream carries a corpus_id
        # (the user's active project), this binding folds "search ONLY corpus X"
        # into the turn's system prompt so the agent's rag_store tools retrieve
        # from the active project's corpus. No active project → no addendum, the
        # persona is byte-identical to before. The framework primitive is agnostic
        # to WHAT the id is; og118's local-first project id is the corpus_id.
        context_prompt=active_corpus_binding(),
        # DD-002C → og118-continuity canary: conversation continuity by CLIENT-SENT
        # history replay. og118 is local-first — the transcript lives in the
        # browser's IndexedDB and the client replays it on each /chat/stream turn
        # (ChatRequest.history). The Runner folds + re-sanitizes it (untrusted
        # context, never authorization) via sanitize_history. So there is NO
        # server-side store and the backend is STATELESS: continuity survives an ACA
        # replica recycle/redeploy/scale automatically (the prior InMemory store was
        # wiped on restart → the model lost the thread mid-conversation). The
        # client_history_max_messages / _chars caps bound per-turn token cost.
        # og118 is a thinking companion, not a coding agent. The COMPANION profile
        # blocks every shell / file-mutation / host-filesystem builtin under BYPASS,
        # so the persona's "you have no filesystem" is TRUE, not asserted (a user
        # asking "show me your code" had made it Glob+Read its own deployment
        # source). The blocked set lives in fi-runner now (the framework home of the
        # #277 fix) so every companion inherits it; rag_store/task_tracker are MCP
        # tools, not builtins, so document search + the glass-box plan are unaffected.
        tool_policy=ToolPolicy.companion(),
        # Punto de extensión para un segundo consumer: un MCP propio, declarado
        # por entorno, sin que og118 tenga que conocerlo. fenix registra aquí su
        # herramienta para guardar la cotización en el expediente del cliente.
        # Formato: FI_EXTRA_MCP="nombre:/ruta/al/modulo.py[,otro:...]".
        # Lista vacía explícita = sin las herramientas del consumer. `None` (el
        # default) lee el entorno y se comporta como siempre.
        extra_mcp_servers=(
            _extra_mcp_desde_entorno() if extra_mcp_servers is None else list(extra_mcp_servers)
        ),
    )
