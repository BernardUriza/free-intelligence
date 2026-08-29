"""og118 Runner — fi-runner sobre la puerta de AIRE.

Un `Runner` compuesto inline con `AIREBackend`: el turno cruza HTTP hacia AIRE,
que envuelve el Agent SDK, guarda el transcript en SU Postgres y monta un
registry de tools vetadas server-side. La ruta local (`ClaudeCodeBackend` con el
OAuth ambiente) se borró el 2026-08-29 con la consolidación de la flota — ver
`fi_runner.backends`.

Lo que este archivo decide, y es todo lo que le queda por decidir: la persona
compuesta, QUÉ tools del registry pide cada runner (`capabilities` →
`registry_tools`) y en qué MODO de la puerta viaja el turno. El stream agéntico
(plan/step/tool_call) lo emite `run_stream`; el hook del frontend lo mapea a los
contratos de core.
"""

from __future__ import annotations

import os
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fi_runner import (
    AIREBackend,
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
# CLAUDE.md vivo por chat y cómo evolucionarlo (persona read/update). Se anexa
# SÓLO si el turno pide la tool `persona` — prometer una herramienta que su
# registry no monta sería mentirle al modelo.
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


# Las tools del registry de AIRE que og118 le da a un turno normal. Nombrado
# porque hay un consumer que necesita MENOS (el tutor del cibercafé): la persona
# decide lo que el modelo QUIERE hacer, las capabilities lo que PUEDE. Cambiar
# sólo la primera no acota nada.
#
#   persona      → read/update sobre la parte viva del CLAUDE.md de la casita
#                  (OG118-LIVING-CLAUDE). Sin ella el párrafo de identidad viva
#                  que la persona anexa promete una tool que no existe.
#   task_tracker → el plan/steps del glass-box (backlog #45)
#   rag_store    → búsqueda en los documentos del proyecto (backlog #46)
#
# `rag_store` ENTRA SÓLO con Proyectos prendido (OG118_PROYECTOS), y la razón no
# es higiene: en og118 el corpus ES el del proyecto (`corpus_id` = el id del
# proyecto), así que con Proyectos apagado esa tool busca en un almacén que nadie
# llena — la mitad de un camino de datos, que es exactamente lo que
# [[both-ends-of-the-data-path]] prohíbe dejar prendido. Y arrastra
# `delete_corpus`, que el modelo puede llamar sin confirmación: una destructiva
# viva para una feature que nadie usa.
def proyectos_activos() -> bool:
    """El mismo interruptor que `app.proyectos_activos`, leído al llamar."""
    return os.getenv("OG118_PROYECTOS", "0").strip().lower() in ("1", "true", "yes", "on")


def capacidades_por_defecto() -> list[str]:
    """Las tools del registry de un turno normal, según el flag."""
    return ["persona", "task_tracker", "rag_store"] if proyectos_activos() else ["persona", "task_tracker"]

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
    model: str,
    project: str | None = None,
    mode: str = MODO_AIRE_POR_DEFECTO,
    registry_tools: tuple[str, ...] = (),
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
    pide del registry de AIRE la tool `persona` (read/update sobre la parte viva
    del CLAUDE.md de la casita), `task_tracker` (backlog #45) y `rag_store`
    (backlog #46): el plan en vivo y la búsqueda en los documentos del proyecto
    dejaron de ser capabilities locales que esta ruta perdía, y vuelven a llegar
    por donde siempre llegaron — tool_calls que el runner traduce sin saber en
    qué puerta corrieron. El corpus vive en la Postgres de AIRE, con la búsqueda
    full-text de Postgres: recupera por PALABRAS, no por parecido semántico, que
    es el techo que se aceptó a cambio de que el corpus no viva en el disco
    mortal del droplet. Y viaja en el modo que el caller fije —
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
        # ACOTADO POR EL CALLER, no fijo. Estaba hardcodeado a las tres, así que
        # un consumer que pedía MENOS —el tutor del cibercafé de fenix, que pide
        # `capabilities=["task_tracker"]` justamente para no heredar rag_store con
        # sus destructivas— las recibía las tres igual. El acotamiento sólo se
        # honraba en la ruta claude-code (donde `capabilities` sí gobernaba los
        # MCP locales); en ésta se perdía en silencio. Ahora la lista viaja.
        registry_tools=registry_tools,
        project_for_turn=AIRE_CHAT_PROJECT.get,
    )


def build_runner(
    persona_path: Path = PERSONA_PATH,
    persona_text: str | None = None,
    # Los NOMBRES de tools del registry de AIRE que este runner pide por turno.
    # Se sigue llamando `capabilities` porque es lo que significa para el
    # consumer —lo que el modelo PUEDE hacer— aunque del otro lado de la puerta
    # ya no sean procesos MCP locales sino tenants vetados del registry.
    capabilities: list[str] | None = None,
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
    # AIRE monta sus tools server-side: sólo el NOMBRE cruza la puerta, y la
    # puerta 422ea cualquiera fuera de su registry. Por eso lo que el caller
    # llama `capabilities` son aquí los `registry_tools` del turno — un consumer
    # que pide MENOS (el tutor del cibercafé) ahora recibe menos de verdad.
    registry_tools = tuple(capacidades_por_defecto() if capabilities is None else capabilities)
    persona_parts = [base_persona, load_prompt(COMPANION_CONSTRAINTS_PATH)]
    # El párrafo de identidad viva le enseña al modelo a llamar
    # `mcp__persona__read/update`, así que va SÓLO si el turno pide esa tool.
    # Anexarlo siempre le prometía al tutor del cibercafé —que pide únicamente
    # task_tracker— una herramienta que su turno no monta: el modelo la llamaría,
    # la puerta la rechazaría, y el usuario vería un error por una capacidad que
    # su propio system prompt le había ofrecido.
    if "persona" in registry_tools:
        persona_parts.append(load_prompt(LIVING_IDENTITY_PATH))
    backend: Any = _backend_aire(model, aire_project, aire_mode, registry_tools)
    # El binding del corpus VIVE O MUERE con su herramienta, y "la herramienta
    # existe" NO era la condición: el 2026-08-24 se prendió con la tool puesta
    # y la subida todavía escribiendo en el store local, así que el corpus
    # estaba siempre vacío y el agente le contestaba al usuario "el acta que
    # mencionas no llegó o no se subió correctamente" sobre un archivo que sí
    # estaba. Una respuesta segura y falsa sobre sus propios archivos.
    #
    # La condición es que LA SUBIDA ESCRIBA DONDE LA BÚSQUEDA LEE, y ahora se
    # cumple: AIRE tiene la puerta HTTP del corpus (backlog #47) y `app.py`
    # enruta su costura de rag_store a `AireCorpusClient`, así que los dos
    # extremos del camino aterrizan en la misma repisa. Ver
    # [[both-ends-of-the-data-path]].
    # Los dos bindings son de Proyectos: uno dice DÓNDE buscar (el corpus activo),
    # el otro CÓMO contestar (las instrucciones del workspace). Con la feature
    # apagada no hay ni corpus ni workspace, así que atar el addendum sería
    # prometerle al modelo un contexto que el turno nunca trae.
    bindings = (
        compose_bindings(active_corpus_binding(), owner_instructions_binding())
        if proyectos_activos()
        else None
    )
    return Runner(
        backend=backend,
        # La narración del flow es una SEGUNDA llamada al mismo backend con el
        # system prompt del narrador. Sobre AIRE eso (a) gasta un segundo turno
        # real por turno de chat y (b) su /init sobreescribiría la base de la
        # casita del chat con el prompt del narrador — rompiendo el invariante de
        # OG118-LIVING-CLAUDE (la base de cada casita ES la persona). El diagrama
        # mecánico del turno se emite igual; sólo se apaga el refinado.
        flow_narrator=None,
        # The Runner must KNOW the model, not just the backend: it is the Runner
        # that stamps the answer's provenance (TurnResult.model → the "powered by"
        # chip). Configured only on the backend, `Runner.model` stayed None and the
        # local route shipped answers that could not say what produced them — while
        # the external-engine route, which reports its own model, could.
        # `chosen_model = model or self.default_model` in the backend, so naming it
        # here changes WHO KNOWS the model, never WHICH model runs.
        model=model,
        persona="\n\n".join(persona_parts),
        # VACÍO A PROPÓSITO: `capabilities` en fi-runner spawnea servidores MCP
        # LOCALES por stdio, y ésos no cruzan la puerta de AIRE. Lo que el caller
        # pidió ya viajó arriba como `registry_tools` del backend — AIRE monta su
        # propio servidor vetado de ese nombre. Poner la lista aquí levantaría
        # subprocesos que nadie consulta.
        capabilities=[],
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
        context_prompt=bindings,
        # DD-002C → og118-continuity canary: conversation continuity by CLIENT-SENT
        # history replay. og118 is local-first — the transcript lives in the
        # browser's IndexedDB and the client replays it on each /chat/stream turn
        # (ChatRequest.history). The Runner folds + re-sanitizes it (untrusted
        # context, never authorization) via sanitize_history. So there is NO
        # server-side store and the backend is STATELESS: continuity survives an ACA
        # replica recycle/redeploy/scale automatically (the prior InMemory store was
        # wiped on restart → the model lost the thread mid-conversation). The
        # client_history_max_messages / _chars caps bound per-turn token cost.
        #
        # El DEFAULT, no `companion()`, y la diferencia importa: AIRE NO reenvía
        # el tool_policy — configura sus tools server-side con el dial de modos, y
        # `AIREBackend._warn_unenforceable` avisa por cada turno que traiga un
        # permission_mode distinto del default. Mandar `companion()` aquí no
        # bloqueaba nada: era una lista de builtins prohibidos que nadie del otro
        # lado de la puerta leía, o sea una garantía escrita y no ejercida. Quien
        # acota los builtins ahora es el modo (`complete` no concede ninguno;
        # `agent` concede Read/Write/Glob/Grep/WebSearch/WebFetch y en ningún modo
        # existe Bash) más la jaula de AIRE, que confina los de archivo a la
        # casita del chat.
        tool_policy=ToolPolicy(),
    )
