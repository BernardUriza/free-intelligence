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
import re
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fi_runner import (
    AIREBackend,
    COMPANION_BLOCKED_BUILTINS,
    ClaudeCodeBackend,
    FlowNarrator,
    MCPServerSpec,
    Runner,
    ToolPolicy,
    active_corpus_binding,
    compose_bindings,
    owner_instructions_binding,
    load_prompt,
)

# La persona base es CONFIGURABLE por entorno para que un segundo consumer
# (apps/fenix) corra este mismo runtime con su propia voz, sin duplicar el
# servidor: "1 build → N consumers". Sin la variable, la ruta es exactamente la
# de antes, así que og118 no cambia en nada. El prompt sigue viviendo en un .md
# que se lee en runtime (P0 prompts-as-content), nunca inline en el código.
PERSONA_PATH = Path(os.environ.get("FI_PERSONA_PATH") or (Path(__file__).parent / "prompts" / "persona.md"))
COMPANION_CONSTRAINTS_PATH = Path(__file__).parent / "prompts" / "companion_constraints.md"
# OG118-LIVING-CLAUDE: el párrafo que le cuenta al agente que su casita tiene un
# CLAUDE.md vivo por chat y cómo evolucionarlo (persona read/update). Solo la
# ruta AIRE lo anexa — en la ruta claude-code esas tools no existen y prometerlas
# sería mentirle al modelo.
LIVING_IDENTITY_PATH = Path(__file__).parent / "prompts" / "living_identity.md"

# La casita del turno (OG118-LIVING-CLAUDE, casita-per-chat). app.py la setea por
# request con el nombre derivado del conversation_id; AIREBackend la resuelve al
# tope de cada turno vía project_for_turn. Un ContextVar y no un atributo mutable
# porque los turnos son concurrentes: cada request lleva su propio contexto.
AIRE_CHAT_PROJECT: ContextVar[str | None] = ContextVar("og118_aire_chat_project", default=None)

_AIRE_NAME_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
_AIRE_NAME_MAX = 128


def aire_project_for_chat(session_id: str | None) -> str | None:
    """El nombre de casita AIRE para un chat: ``{base}-{conversation_id}``.

    El prefijo es la casita base del deploy (``OG118_AIRE_PROJECT``, default
    ``og118``): así un segundo consumer de este runtime (apps/fenix) nombra sus
    chats con SU identidad — ``fenix-{chat}`` — sin tocar este archivo. Sin la
    variable el nombre es byte-idéntico al de siempre.

    El id viene del cliente (no confiable): se filtra al allowlist de AIRE
    (``[A-Za-z0-9_-]``, 128 max — server/aire/names.py) en vez de rechazarse,
    porque aquí el nombre lo construimos nosotros, no lo ejecuta un path. Sin id
    utilizable → None, y el backend cae a su proyecto fijo (una casita
    compartida, el comportamiento pre-feature)."""
    if not session_id:
        return None
    cleaned = _AIRE_NAME_UNSAFE.sub("", session_id)
    if not cleaned:
        return None
    base = os.getenv("OG118_AIRE_PROJECT", "og118")
    return f"{base}-{cleaned}"[:_AIRE_NAME_MAX]


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


# OG118_BACKEND selecciona el motor del turno (aire-server backlog #35: la flota
# fi entra por la puerta del engine de AIRE, con AIREBackend como puente
# sancionado — PR #408). "claude-code" (default, y el deploy de hoy) es la ruta
# de siempre: BackendAcotado spawnea el CLI con el OAuth ambiente, byte-idéntica
# sin la variable. "aire" habla HTTP con AIRE — el servidor siempre-arriba de
# Bernard que envuelve el Agent SDK y guarda el transcript crudo en SU Postgres.
MOTOR_POR_DEFECTO = "claude-code"

# El MODO de la puerta que monta cada turno de la ruta aire. El dial de AIRE
# tiene exactamente dos muescas (aire-server `server/aire/engine/options.py`,
# `MODES`) y son paquetes cerrados, no una lista de tools a la carta:
#
#   complete → allowed_tools []            · Bash/Read/Write/Edit/Glob/Grep/
#                                            WebSearch/WebFetch prohibidos
#              permission_mode "default"
#   agent    → allowed_tools Read, Write, Glob, Grep, WebSearch, WebFetch
#              · Bash prohibido · permission_mode "acceptEdits"
#
# En las dos, las tools del registry que el turno pide (`tools=[…]`) se suman a
# `allowed_tools`; desde aire-server 5ae8e33 eso también corre en complete.
#
# `complete` es el default y lo que og118 quiere: la persona y nada más. `agent`
# se pide SÓLO cuando la búsqueda en internet es load-bearing para el producto
# —el tutor del cibercafé de fenix—, y entonces se acepta el paquete COMPLETO:
# el dial no sabe conceder WebSearch a solas (hueco nombrado en aire-server
# backlog #37). Lo que amortigua ese paquete es la jaula de AIRE (backlog #24,
# un hook PreToolUse): los tools de archivo quedan confinados a la casita del
# chat, así que Read/Write no alcanzan `/etc/aire/env` ni `/tmp`, y Bash no
# existe en ningún modo.
MODO_AIRE_POR_DEFECTO = "complete"


def _backend_aire(
    model: str, project: str | None = None, mode: str = MODO_AIRE_POR_DEFECTO
) -> AIREBackend:
    """El puente a AIRE, con la identidad de og118 como proyecto (su casita).

    AIRE es dueño del lado servidor: la memoria (su session_store en su
    Postgres), las tools (un registry vetted que 422ea cualquier nombre fuera de
    él) y los permisos. Por eso esta ruta NO recibe el session_store inyectado
    ni las capabilities MCP locales — task_tracker/rag_store corren como
    procesos locales y no existen en el droplet. La continuidad sigue siendo el
    history replay del cliente, exactamente como hoy. La puerta se configura con
    AIRE_GATE_URL y AIRE_AUTH_TOKEN (AIREBackend los lee del entorno).

    OG118-LIVING-CLAUDE: cada chat vive en SU casita (project_for_turn lee
    AIRE_CHAT_PROJECT, que app.py setea por request como og118-{chat}); el
    proyecto fijo queda de fallback para turnos sin conversación. Cada turno
    pide la tool `persona` del registry de AIRE (read/update sobre la parte
    viva del CLAUDE.md de la casita), y viaja en el modo que el caller fije —
    `complete` por default: desde aire-server 5ae8e33 la puerta corre registry
    tools en complete, así que og118 tiene su persona viva sin cargar los
    builtins del preset agent, que no quiere.

    `mode` (opcional) sube el turno a `agent` para un consumer cuyo producto
    depende de buscar en internet (el tutor del cibercafé de fenix). Ver
    `MODO_AIRE_POR_DEFECTO` arriba para qué concede exactamente cada muesca y
    por qué no hay una tercera.

    Nacimiento delgado (aire-server ef21e68): la persona completa vive UNA sola
    vez en la casita base og118 (AIREBackend la init-ea antes del primer chat);
    cada casita de chat nace con el stub `@base og118`, que el engine
    dereferencia en cada spawn — un solo origen vivo de la persona en vez de N
    copias congeladas.

    `project` (opcional) fija OTRA casita base para ESTE runner, ganándole al
    entorno: un consumer con dos personas en el mismo proceso (fenix: mostrador
    y tutor) necesita dos bases — si compartieran una, cada runner init-earía la
    misma casita con SU persona compuesta y el último en arrancar ganaría,
    dejando a los chats del otro producto dereferenciando la voz equivocada."""
    return AIREBackend(
        project=project or os.getenv("OG118_AIRE_PROJECT", "og118"),
        default_model=model,
        default_mode=mode,
        registry_tools=("persona",),
        project_for_turn=AIRE_CHAT_PROJECT.get,
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
    aire_project: str | None = None,
    aire_mode: str = MODO_AIRE_POR_DEFECTO,
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
    promise background/async work it cannot do.

    `aire_project` (only meaningful on the aire route) pins THIS runner's base
    casita, overriding the deploy-wide `OG118_AIRE_PROJECT` — the seam a
    consumer with a second persona in the same process (fenix's tutor) uses so
    each voice owns its own base instead of fighting over one.

    `aire_mode` (also aire-only) picks the door mode every turn of THIS runner
    rides. `complete` (the default) keeps the turn tool-free but for the AIRE
    registry tools it asks for; `agent` is the only way the door grants
    WebSearch/WebFetch, and it grants Read/Write/Glob/Grep with it — caged to
    the chat's casita, Bash excluded. See `MODO_AIRE_POR_DEFECTO`."""
    base_persona = persona_text if persona_text is not None else load_prompt(persona_path)
    model = os.getenv("OG118_MODEL", "claude-sonnet-4-5")
    motor = os.getenv("OG118_BACKEND", MOTOR_POR_DEFECTO).strip().lower()
    persona_parts = [base_persona, load_prompt(COMPANION_CONSTRAINTS_PATH)]
    if motor == "aire":
        backend: Any = _backend_aire(model, aire_project, aire_mode)
        # Solo esta ruta tiene la tool persona (registry de AIRE): el párrafo de
        # identidad viva viaja con la base al /init de cada casita-por-chat.
        persona_parts.append(load_prompt(LIVING_IDENTITY_PATH))
        # AIRE monta sus propias tools server-side; los MCP locales no viajan
        # (la puerta 422ea nombres fuera de su registry). Forzar las listas a
        # vacío aquí — no confiar en que cada caller lo recuerde.
        capabilities = []
        extra_mcp_servers = []
    else:
        backend = BackendAcotado(default_model=model, session_store=session_store)
    return Runner(
        # session_store (og118-session-store wiring): the SDK's native durable
        # memory, INJECTED by app.py's lifespan when OG118_SESSION_STORE_DSN is
        # set (Postgres). With it, the Runner prefers resume= over re-folding the
        # client's history replay — the transcript (tool_use/tool_result included)
        # survives a recycled container and the per-turn re-send disappears.
        # None (the default, and today's deploy) keeps the turn byte-identical:
        # client history replay stays the continuity.
        backend=backend,
        # La narración del flow es una SEGUNDA llamada al mismo backend con el
        # system prompt del narrador. En la ruta AIRE eso (a) gasta un segundo
        # turno real por turno de chat y (b) su /init sobreescribiría la base de
        # la casita del chat con el prompt del narrador — rompiendo el invariante
        # de OG118-LIVING-CLAUDE (la base de cada casita ES la persona). El
        # diagrama mecánico del turno se emite igual; solo se apaga el refinado.
        flow_narrator=None if motor == "aire" else FlowNarrator(),
        # The Runner must KNOW the model, not just the backend: it is the Runner
        # that stamps the answer's provenance (TurnResult.model → the "powered by"
        # chip). Configured only on the backend, `Runner.model` stayed None and the
        # local route shipped answers that could not say what produced them — while
        # the external-engine route, which reports its own model, could.
        # `chosen_model = model or self.default_model` in the backend, so naming it
        # here changes WHO KNOWS the model, never WHICH model runs.
        model=model,
        persona="\n\n".join(persona_parts),
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
        # Two concerns, two bindings, ONE context_prompt (the Runner holds one).
        # The owner's workspace instructions go LAST so they sit closest to the
        # user message: the corpus binding says WHERE to look, the owner says HOW
        # to answer, and the owner's voice is the one that should still be in
        # earshot when the model starts writing.
        context_prompt=compose_bindings(active_corpus_binding(), owner_instructions_binding()),
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
