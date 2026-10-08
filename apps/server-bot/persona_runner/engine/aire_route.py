"""The AIRE turn route — every persona turn rides AIRE's engine door instead
of a Claude Agent SDK hosted in this container.

Stage 2 of the AIRE migration (backlog ``aire-engine-stage2.md``). The mapping,
decided by Bernard 2026-08-22:

- **Casita = persona+channel**: base casita ``{persona_id}`` holds the persona
  DNA (installed once via ``/init``); each chat casita
  ``{persona_id}-{channel_id}`` is born THIN with the ``@base`` stub the engine
  dereferences at every spawn (aire-server ef21e68 / og118 PR #413).
- **Session = TOPIC** (Bernard, 2026-08-22 — *"por sesión de discord bot y por
  channel y por topic temporal"*). The casita is the channel's SOUL and persists;
  the session inside it rolls over after ``AIRE_TOPIC_IDLE_TIMEOUT_S`` of channel
  silence, so a channel that lives for years stops meaning one transcript that
  grows forever. The id is durable (a row per casita in Postgres), because an
  in-RAM one would fork the topic on every redeploy. Full reasoning, the atomic
  claim and the fallback: ``engine/aire_topic.py``.
- **Facts + behavioral_guidance travel IN-BAND**: the runner reads the author's
  facts from Khimeras Postgres and composes them into the turn message, exactly
  as it composes turn_context — no Khimeras credential ever reaches the droplet.
  AIRE's registry tools ``persona`` + ``memory`` ride every turn, so the agent
  keeps a living identity and transcript recall.
- **Model routing rides the door per turn** (aire-server #29) — and since
  aire-server #38 AIRE HONOURS it on a WARM session too: a turn that names a
  different shape drops the pooled client first (one cache-creation, no memory
  lost — the transcript resumes from Postgres). Re-measured live 2026-08-28
  against ``gate.bernarduriza.com``: two turns on one session, haiku then
  ``claude-sonnet-4-6``, each answered by the model it asked for. The
  divergence window is now at most ONE in-flight turn. ``model_diverged``
  stays as the tripwire; a recurrence means AIRE regressed.
- **Concurrency is guarded structurally, never by a knob's current value**
  (code review, 2026-08-22). A turn holds its casita's lock across
  decide→turn→mark, so two messages arriving together in one channel cannot both
  believe they open the session and fold the history twice (``CasitaState``). A
  judge's casita is NAMED after the digest of its system prompt, so two judges
  can never share an overwritable ``/init`` surface no matter what
  ``JUDGE_MAX_CONCURRENCY`` is set to (``judge_casita_for``).
- **Terminal errors stay errors**: ``budget_exhausted`` / ``credentials_exhausted``
  (aire #23/#31 family) map to 500 (retries cannot fix them; the gateway's
  neutral in-character error path takes over); ``slot_busy`` backpressure maps
  to 503 (the gateway's transient retry applies). A cut turn never looks like
  success.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field

import structlog
from fastapi import HTTPException
from fi_runner import AIREBackend
from fi_runner.backend import BackendError, MCPServerSpec, ToolPolicy, TurnDocument, TurnImage

from persona_core.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt
from persona_runner.core import config
from persona_runner.core.schemas import JudgeRequest, JudgeResponse, TurnRequest, TurnResponse
from persona_runner.engine import aire_principal, aire_topic, auth_failure
from persona_runner.engine.framing import fold_history, frame_turn_text
from persona_runner.engine.persona_files import load_persona, resolve_persona_path

log = structlog.get_logger()

# The registry tools every persona turn requests from AIRE (vetted server-side):
# `persona` = the living half of the casita's CLAUDE.md, `memory` = recall over
# the session's own transcript in AIRE's session store.
AIRE_REQUIRED_TOOLS = ("persona", "memory")
# Built-in Claude Code tools a persona turn MUST be able to call. WebSearch is
# load-bearing and its absence fails SILENTLY (the agent simply never searches
# and deflects with banter, 2026-06-14). Lived in `engine.options` while the
# local SDK host existed; the audit below asserts AIRE's mode grants them.
REQUIRED_BUILTIN_TOOLS = ("WebSearch", "WebFetch")
# WebSearch/WebFetch exist ONLY in AIRE's `agent` mode (server-side MODES dial,
# verified in aire-server engine/options.py 2026-08-22, which also excludes Bash
# there and cages file tools to the casita). Any other mode silently strips the
# load-bearing web tools — the same silent degradation verify_required_tools
# exists to kill — so the allowlist is exactly one mode.
AIRE_ALLOWED_MODES = ("agent",)
# The BUILTIN surface AIRE's server-side mode dial actually grants, AUDITED
# against aire-server `server/aire/engine/options.py::MODES` at ef21e684
# (2026-08-22). This repo cannot ENFORCE it — the dial lives on the droplet, and
# the door ships no per-turn builtin denylist (named as an AIRE-side gap in the
# stage-2 backlog). So the table is a RECORDED AUDIT and the boot check asserts
# OUR config against it: a mode regression here crashes the boot, a change on
# AIRE's side stays invisible until re-audited. Say so, never imply enforcement.
AUDITED_MODE_ALLOWS = {
    "agent": ("Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch"),
    "complete": (),
}
AUDITED_MODE_DENIES = {
    "agent": ("Bash",),
    "complete": ("Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"),
}
# The honest delta from `options.FORBIDDEN_BUILTIN_TOOLS`: AIRE's `agent` mode
# grants Write (and reaches Edit under acceptEdits), which the local route
# forbids. It is ACCEPTED, not hidden, on two verified grounds: aire-server's
# `engine/cage.py` PreToolUse hook denies any file tool resolving outside the
# session's casita, and the droplet holds NO Khimeras credential — POSTGRES_URL
# and the fleet OAuth never leave this container, so the 2026-08-10 threat (a
# shell where the secrets are) does not transfer. Logged loudly at every boot so
# the new capability can never become silent.
AIRE_ACCEPTED_TOOL_DELTA = ("Write", "Edit")
# AIRE's structured error CODES, classified once. Terminal cuts (aire #23/#31)
# cannot be fixed by retrying; backpressure can.
# attachments_lost (aire-server #50): the door attached fewer images than were
# sent. A retry resends the same references, so it is terminal, never 502.
# attachment_budget (aire-server #50): the session already carries too many
# attachments; every later turn resends them, so a retry can only be refused again.
_TERMINAL_ERRORS = (
    "budget_exhausted",
    "credentials_exhausted",
    "budget_exceeded",
    "attachments_lost",
    "attachment_budget",
)
# A 4xx from the door is AIRE refusing THIS request (bad shape, oversize or
# expired attachment, full session): resending it byte-identical cannot pass,
# and each retry re-fetches the attachments. Only these two 4xx are transient.
_RETRYABLE_4XX = (408, 429)
_BACKPRESSURE_ERRORS = ("slot_busy",)
_STATUS_PREFIX = {500: "aire turn terminal", 503: "aire backpressure", 502: "aire turn failed"}

_NAME_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
_NAME_MAX = 128


def memory_tool_specs(casita: str) -> list[MCPServerSpec]:
    """The persona_memory HTTP MCP spec for THIS casita — the 9 tools the AIRE
    route lost, hosted here where the Khimeras credentials live (api/mcp_http).

    Feature-gated on BOTH env vars: RUNNER_MCP_BASE (this runner's public
    https origin, which must also sit in AIRE's AIRE_REMOTE_TOOL_ORIGINS) and
    RUNNER_MCP_TOKEN (the bearer the endpoint demands back). Either absent →
    no spec, and the turn runs exactly as before this feature existed."""
    base = os.environ.get("RUNNER_MCP_BASE", "").strip().rstrip("/")
    token = os.environ.get("RUNNER_MCP_TOKEN", "").strip()
    if not base or not token:
        return []
    return [
        MCPServerSpec(
            name="persona_memory",
            url=f"{base}/mcp/{casita}",
            headers={"Authorization": f"Bearer {token}"},
        )
    ]


# The casita THIS turn addresses — a ContextVar (not a mutable attribute)
# because turns are concurrent; AIREBackend resolves it at the top of each turn.
_chat_casita: ContextVar[str | None] = ContextVar("aire_chat_casita", default=None)
_backends: dict[str, AIREBackend] = {}
_judge_backends: dict[str, AIREBackend] = {}
_default_policy = ToolPolicy()


@dataclass
class CasitaState:
    """One casita's turn gate plus its mirror of the durable topic row.

    ``lock`` is why both live in one object: choosing the TOPIC, running the
    turn and marking it answered must all happen under it. Without it two
    near-simultaneous messages in one Discord channel could both believe they
    open the session and BOTH fold the whole replayed history into their
    message. AIRE serializes execution with a per-session lock, so nothing
    crashes — the session simply ends up holding the conversation twice, and
    those tokens are paid twice. This is the same invariant api/turn.py states
    as "only under the lock does 'not open' mean THIS turn opens the session";
    holding it also serializes same-channel turns runner-side, which matches the
    local path and is what AIRE would do anyway.

    The topic decision belongs INSIDE this lock for the same reason: two
    messages arriving together must land in ONE topic, never fork it.

    ``topic`` is a MIRROR, never the source. The topic id and the
    already-answered bit are durable (``aire_topic``); this copy only serves the
    Postgres-is-down fallback and vetoes a second history fold when a
    ``mark_answered`` write is lost. The old in-RAM ``seen`` bit it replaces was
    the reason a restart re-folded history — that is now decided by the row.
    """

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    topic: aire_topic.TopicMemory = field(default_factory=aire_topic.TopicMemory)


# One entry per (persona, channel) EVER served, each carrying an asyncio.Lock —
# so this dict is heavier than the plain string set it replaces and cannot be
# left to grow forever: a gateway that meets 50k distinct channels would hold
# 50k locks it can never drop. The cap evicts the least-recently-used IDLE entry
# (never one whose lock is held). An eviction costs nothing but the topic MIRROR
# — the topic id and its answered bit live in Postgres, so the evicted casita's
# next turn re-reads exactly what it had.
_CASITA_STATE_MAX = int(os.environ.get("AIRE_CASITA_STATE_MAX", "4096"))
_casita_state: OrderedDict[str, CasitaState] = OrderedDict()


def casita_state(casita: str) -> CasitaState:
    """This casita's gate + topic mirror, created on first use.

    Keyed by the CASITA, not by casita+session: the session is now the topic and
    the topic is chosen under this very lock, so a key that carried it would have
    to be known before the thing it decides.

    Creation is a single synchronous step (no await between the miss and the
    insert), the setdefault pattern the old session pool's slot_lock used — so two
    coroutines can never walk away holding two different locks for one casita,
    which would reopen the very race the lock closes.
    """
    state = _casita_state.get(casita)
    if state is None:
        state = CasitaState()
        _casita_state[casita] = state
        _evict_cold_casitas()
    _casita_state.move_to_end(casita)
    return state


def _evict_cold_casitas() -> None:
    """Drop least-recently-used IDLE casitas until the cap holds again."""
    while len(_casita_state) > _CASITA_STATE_MAX:
        victim = next((k for k, s in _casita_state.items() if not s.lock.locked()), None)
        if victim is None:
            return  # every casita is mid-turn: correctness outranks the cap
        del _casita_state[victim]


def verify_aire_route() -> None:
    """Crash the boot LOUDLY when the AIRE route's capability surface is wrong.

    The AIRE twin of ``options.verify_required_tools``: WebSearch is load-bearing
    and its absence fails silently, so a runner that would ship turns in a mode
    without it must never come up. Env is checked too — a missing gate URL/token
    falling back to a dead default is the fake-green AGENTS.md prohibits.
    """
    gate = os.environ.get("AIRE_GATE_URL", "")
    token = os.environ.get("AIRE_AUTH_TOKEN", "") or os.environ.get("AIRE_CANARY_TOKEN", "")
    if not gate or not token:
        raise RuntimeError(
            "The AIRE route requires AIRE_GATE_URL and AIRE_AUTH_TOKEN in the "
            "environment (set out-of-band, see docs/runbook_dr.md) — refusing to "
            "boot a runner whose every turn would 502."
        )
    if config.AIRE_TURN_MODE not in AIRE_ALLOWED_MODES:
        raise RuntimeError(
            f"AIRE_TURN_MODE={config.AIRE_TURN_MODE!r} is not in {AIRE_ALLOWED_MODES}: "
            "WebSearch/WebFetch only exist in AIRE's `agent` mode, so any other mode "
            "silently strips the load-bearing web tools (2026-06-14 class)."
        )
    verify_audited_surface(config.AIRE_TURN_MODE)
    # Assert the REAL wiring, exactly as the boot's capability check demands
    # for the local route: the backend a turn would actually get must carry the
    # required registry tools and ride an allowlisted mode. It is BUILT, not
    # cached — verifying must not mutate module state, or the boot check quietly
    # becomes a warm-up whose side effect nothing declares.
    backend = _build_backend(base_persona_id(None))
    missing = [t for t in AIRE_REQUIRED_TOOLS if t not in backend.registry_tools]
    if missing:
        raise RuntimeError(
            f"The AIRE route is missing required registry tools {missing} "
            f"(configured: {list(backend.registry_tools)}) — the persona would lose "
            "its living identity or transcript recall silently."
        )
    if backend.default_mode not in AIRE_ALLOWED_MODES:
        raise RuntimeError(f"AIRE backend rides mode {backend.default_mode!r}, not in {AIRE_ALLOWED_MODES}")


def verify_audited_surface(mode: str) -> None:
    """Assert the mode's RECORDED surface in both directions, exactly like
    ``options.verify_required_tools`` does for the local route.

    Missing a required built-in ships a runner that boots ``healthy`` and
    deflects every factual question (2026-06-14); carrying a shell hands whoever
    types in Discord one (2026-08-10). Here the surface is server-side, so what
    is asserted is OUR config against the audit table — which is precisely what
    catches the regression this repo can commit (a mode swap), and precisely what
    cannot catch a change made on the droplet.
    """
    allows = AUDITED_MODE_ALLOWS.get(mode, ())
    denies = AUDITED_MODE_DENIES.get(mode, ())
    missing = [t for t in REQUIRED_BUILTIN_TOOLS if t not in allows]
    if missing:
        raise RuntimeError(
            f"AIRE mode {mode!r} does not grant required built-ins {missing} "
            f"(audited surface: {list(allows)}) — web search is load-bearing and "
            "must not degrade silently."
        )
    if "Bash" not in denies:
        raise RuntimeError(
            f"AIRE mode {mode!r} does not deny Bash (audited denies: {list(denies)}) — "
            "a persona turn must never reach a shell."
        )
    reachable = [t for t in AIRE_ACCEPTED_TOOL_DELTA if t in allows or mode == "agent"]
    log.warning(
        "aire_route_accepted_tool_delta",
        mode=mode,
        reachable_but_forbidden_locally=reachable,
        compensating_control="aire-server engine/cage.py confines file tools to the casita",
        note="the droplet holds no Khimeras credential; POSTGRES_URL and the fleet OAuth stay here",
    )


def base_persona_id(persona_id: str | None) -> str:
    """The canonical persona id a turn resolves to — the DNA file's stem, so an
    unknown/invalid id names the DEFAULT persona's casita, matching exactly which
    DNA ``load_persona`` will return for it (never a casita/DNA mismatch)."""
    return resolve_persona_path(persona_id).stem


def chat_casita_for(base_id: str, channel_id: str) -> str:
    """The per-chat casita name: ``{persona}-{channel}``, filtered to AIRE's
    name allowlist (``[A-Za-z0-9_-]``, 128 max — aire-server names.py)."""
    cleaned = _NAME_UNSAFE.sub("", channel_id) or "unknown"
    return f"{base_id}-{cleaned}"[:_NAME_MAX]


def _build_backend(base_id: str) -> AIREBackend:
    """Construct (and never cache) this persona's door client. The single place
    the turn backend's shape is decided, so the boot check can assert the real
    wiring without warming the cache."""
    return AIREBackend(
        project=base_id,
        default_mode=config.AIRE_TURN_MODE,
        registry_tools=AIRE_REQUIRED_TOOLS,
        project_for_turn=_chat_casita.get,
        timeout=config.TURN_TIMEOUT_S,
    )


def backend_for(base_id: str) -> AIREBackend:
    """This persona's door client, created on first use. One backend per persona
    because the thin-birth BASE casita is the backend's fixed ``project``."""
    backend = _backends.get(base_id)
    if backend is None:
        backend = _build_backend(base_id)
        _backends[base_id] = backend
    return backend


async def close_backends() -> None:
    """Close every door client this process opened — turn AND judge (shutdown).

    ``AIREBackend`` holds a pooled ``httpx.AsyncClient``; ``aclose()`` existed
    and nothing called it, so every backend's connections and TLS sessions
    leaked past shutdown. Best-effort per backend: one refusing to close must
    not leave the rest open.
    """
    backends = list(_backends.values()) + list(_judge_backends.values())
    _backends.clear()
    _judge_backends.clear()
    for backend in backends:
        try:
            await backend.aclose()
        except Exception:
            log.exception("aire_route_backend_close_failed", project=getattr(backend, "project", "?"))
    log.info("aire_route_backends_closed", closed=len(backends))


async def fetch_user_facts(user_id: str) -> str:
    """The author's accumulated facts, read from Khimeras Postgres to travel
    IN-BAND in the turn message (the AIRE droplet never gets the credential).

    Same query as the ``persona_memory`` MCP tool ``get_user_facts`` — that tool
    cannot run on AIRE, so the runner pre-fetches what it used to serve. Any
    fault returns "" — a memory-less turn beats a dead one (DB failures never
    kill the turn, repo law).

    Runs on a POOLED connection (``mcp_tools.shared.acquire``). The MCP tool it
    replaces was called only when the model chose to reach for memory; this
    pre-fetch fires on EVERY turn, so the one-shot connect + TLS handshake +
    close it used to inherit became an unconditional cost on the hot path."""
    from persona_runner.mcp_tools import shared

    try:
        async with shared.acquire() as conn:
            if conn is None:
                return ""
            rows = await conn.fetch(
                "SELECT category, fact FROM principal_facts "
                "WHERE principal_id = $1 AND deleted_at IS NULL "
                "ORDER BY updated_at DESC",
                user_id,
            )
    except Exception:
        log.exception("aire_route_facts_fetch_failed", user_id=user_id)
        return ""
    lines = [f"- [{r['category'] or 'uncategorized'}] {r['fact']}" for r in rows]
    return "\n".join(lines)[: config.AIRE_FACTS_MAX_CHARS]


def refs_from_attachments(attachments: list[dict] | None) -> tuple[list[TurnImage], list[TurnDocument], int]:
    """Split the gateway's URL-source blocks into AIRE references.

    Every attachment travels by reference since aire-server #50: an image block
    becomes ``TurnImage(url)``, a document block (PDF or text — AIRE detects
    which) becomes ``TurnDocument(url, title)``. Anything else — an inline
    base64 block no producer emits any more — is DROPPED and counted, so the
    caller logs it instead of losing it silently. Returns
    (images, documents, dropped)."""
    images: list[TurnImage] = []
    documents: list[TurnDocument] = []
    dropped = 0
    for block in attachments or []:
        source = (block or {}).get("source") or {}
        url = source.get("url") if source.get("type") == "url" else None
        if block.get("type") == "image" and url:
            images.append(TurnImage(url=url))
        elif block.get("type") == "document" and url:
            documents.append(TurnDocument(url=url, title=block.get("title") or ""))
        else:
            dropped += 1
    return images, documents, dropped


def _error_status(exc: BackendError) -> int:
    """Classify a door failure by AIRE's structured error CODE, not by its prose.

    ``AIREDoorError`` carries the code (and the door's HTTP status) as data, so
    the decision is made on the datum AIRE actually emits. Substring matching
    survives ONLY as the fallback for an unstructured failure: that way the day
    AIRE rewords a message the worst case is 502-and-retry, never a terminal cut
    misread as something a retry can fix (nor the reverse — a retry storm
    against an exhausted pool).
    """
    code = getattr(exc, "code", None)
    if code is not None:
        if code in _TERMINAL_ERRORS:
            return 500
        return 503 if code in _BACKPRESSURE_ERRORS else 502
    status = getattr(exc, "http_status", None)
    if status == 503:
        return 503
    if isinstance(status, int) and 400 <= status < 500 and status not in _RETRYABLE_4XX:
        return 500
    detail = str(exc)
    if any(known in detail for known in _TERMINAL_ERRORS):
        return 500
    if any(known in detail for known in _BACKPRESSURE_ERRORS) or "AIRE door 503" in detail:
        return 503
    return 502


def to_http_error(exc: BackendError) -> HTTPException:
    """Map a door failure onto the runner's HTTP error contract (the gateway's
    agent_client branches on status: 502/503 retry as mid-restart, 500 never).

    Terminal cuts (budget/credentials — aire #23/#31 family) are 500: no retry
    fixes an exhausted pool, and the gateway's neutral in-character error path
    must take over instead of a retry storm. Backpressure (slot_busy / a door
    503) is 503 so the existing transient retry applies. Everything else is 502.
    """
    status = _error_status(exc)
    return HTTPException(status, f"{_STATUS_PREFIX[status]}: {str(exc)[:200]}")


def log_topic_decision(casita: str, claim: aire_topic.TopicClaim) -> None:
    """Announce a topic boundary as its OWN event.

    A rollover is a context reset: the channel's next answer is written by an
    agent whose transcript is empty. That is exactly the kind of thing this repo
    has been bitten by when it happened silently (a capability quietly not
    happening, 2026-06-14), so it gets a line of its own rather than a field
    buried in the turn line — grep-able, countable, and carrying the idle gap
    that caused it plus the cold-start it costs.

    The first topic a casita ever gets is an OPENING, not a rollover: nothing was
    reset, so it must not be counted as a reset.
    """
    if claim.rolled_over:
        log.info(
            "aire_route_topic_rolled_over",
            casita=casita,
            topic=claim.topic_id,
            previous_topic=claim.previous_topic_id,
            idle_s=int(claim.idle_s),
            window_s=int(config.AIRE_TOPIC_IDLE_TIMEOUT_S),
            durable=claim.durable,
            cost="cold AIRE session: the persona system prompt is cache-created again",
        )
    elif claim.opened:
        log.info(
            "aire_route_topic_opened",
            casita=casita,
            topic=claim.topic_id,
            durable=claim.durable,
        )
    if not claim.durable:
        # The decision was made in RAM because Postgres was unreachable. Say so
        # on every turn it happens: while this is true a restart forks the topic,
        # which is precisely the failure the durable row exists to prevent.
        log.warning(
            "aire_route_topic_not_durable",
            casita=casita,
            topic=claim.topic_id,
            detail="topic decided from this process's memory; a restart now would fork the topic",
        )


_RESUME_PROMPT_CACHE: PromptCache = {}


def resume_note() -> str:
    return load_prompt(SHARED_PROMPTS_DIR, "turn_resume_note", _RESUME_PROMPT_CACHE)


async def turn_ledger_mark_sent(job_id: str) -> None:
    from persona_runner.engine import turn_jobs

    await turn_jobs.LEDGER.mark_aire_sent(job_id)


async def turn_via_aire(req: TurnRequest) -> TurnResponse:
    """One persona turn through AIRE's engine door.

    The whole decide-topic → turn → mark window runs under the casita's lock, so
    "first turn of this topic" can only be true for the turn that actually opens
    it (see ``CasitaState``), and two messages landing together in one channel
    land in ONE topic. They are serialized here, exactly as api/turn.py
    serializes them on the local path.
    """
    base_id = base_persona_id(req.persona_id)
    casita = chat_casita_for(base_id, req.channel_id)
    state = casita_state(casita)
    async with state.lock:
        return await _run_turn(req, base_id, casita, state)


async def _run_turn(req: TurnRequest, base_id: str, casita: str, state: CasitaState) -> TurnResponse:
    """The turn itself. ALWAYS called under ``state.lock`` — see ``turn_via_aire``."""
    from persona_runner.routing.router_runtime import route_model

    start = time.monotonic()
    # The topic decision is the first thing under the lock: it names the AIRE
    # session this turn addresses AND decides whether the caller's replayed
    # history has to be folded in. `needs_fold` is "AIRE's session for this topic
    # is empty", which is what `is_first_turn` has to mean now that a casita
    # outlives many sessions.
    claim = await aire_topic.claim(casita, state.topic)
    log_topic_decision(casita, claim)
    # Un turno REANUDADO (el runner anterior murió a media generación) ya cruzó
    # a AIRE una vez: la historia no se vuelve a plegar y la guía lleva la nota
    # de reintento, para que el modelo repita en vez de comentar el corte.
    is_first_turn = claim.needs_fold and not req.resumed
    guidance = req.behavioral_guidance
    if req.resumed:
        note = resume_note()
        guidance = f"{guidance}\n\n{note}" if guidance else note
        log.warning("aire_route_turn_resumed", casita=casita, topic=claim.topic_id, job_id=req.job_id)

    model, route_meta = await route_model(req.channel_id, req.user_id, req.user_text)
    memory_block = await fetch_user_facts(req.user_id)
    framed = frame_turn_text(
        channel_id=req.channel_id,
        user_id=req.user_id,
        user_text=req.user_text,
        behavioral_guidance=guidance,
        history_block=fold_history(req.history) if is_first_turn else "",
        memory_block=memory_block,
    )
    images, documents, dropped = refs_from_attachments(req.attachments)
    if dropped:
        log.warning(
            "aire_route_attachments_dropped",
            job_id=req.job_id,
            channel_id=req.channel_id,
            dropped=dropped,
            forwarded=len(images),
            documents=len(documents),
        )

    backend = backend_for(base_id)
    remote_specs = memory_tool_specs(casita)
    principal_bound = False
    if remote_specs:
        # The remote tools resolve identity from this durable row (the server
        # binds it, the model never asks — engine/aire_principal). Published
        # under the casita lock, so the live row IS the turn being served.
        principal_bound = await aire_principal.bind(
            casita, user_id=req.user_id, channel_id=req.channel_id, agent_id=base_id
        )
        if not principal_bound:
            remote_specs = []  # no identity, no memory tools — never a guessed user

    async def send_turn():
        return await backend.run_turn(
            system_prompt=load_persona(req.persona_id),
            user_message=framed,
            mcp_servers=remote_specs,
            tool_policy=_default_policy,
            model=model,
            session_id=claim.topic_id,
            images=images or None,
            documents=documents or None,
        )

    token = _chat_casita.set(casita)
    try:
        if req.job_id:
            # La fila sabe desde aquí que el mensaje cruzó (o va a cruzar) a
            # AIRE: una reanudación posterior no vuelve a plegar la historia.
            await turn_ledger_mark_sent(req.job_id)
        try:
            result = await send_turn()
        except BackendError as first:
            # AIRE's budget cut (#23) retires the spent client and its error
            # text prescribes the cure: "send the turn again to continue". ONE
            # resend rides a fresh client that resumes the same session; without
            # it the persona answered "…" every time a pooled client crossed its
            # $ ceiling mid-conversation (the 2026-08-26 P1). A second cut in a
            # row is a real fault and maps to 500 exactly as before.
            if getattr(first, "code", None) != "budget_exhausted":
                raise
            log.warning(
                "aire_route_budget_cut_retrying",
                job_id=req.job_id,
                casita=casita,
                topic=claim.topic_id,
                channel_id=req.channel_id,
            )
            result = await send_turn()
    except BackendError as exc:
        log.error(
            "aire_route_turn_failed",
            job_id=req.job_id,
            channel_id=req.channel_id,
            user_id=req.user_id,
            casita=casita,
            topic=claim.topic_id,
            error=str(exc)[:300],
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
        # /health's `credentials_rejected` used to be set by the local SDK path;
        # with that path gone, THIS is the only place a dead upstream credential
        # (now the droplet's, surfaced as AIRE's structured code) can be seen.
        # Without it the field is a green that cannot fail (verify-before-assuming
        # Rule 22).
        if getattr(exc, "code", None) == "credentials_exhausted":
            auth_failure.mark_failure(str(exc)[:200])
        raise to_http_error(exc) from exc
    finally:
        _chat_casita.reset(token)
        if principal_bound:
            await aire_principal.clear(casita)

    auth_failure.clear_failure()
    # Only a turn that SUCCEEDED marks the topic answered: a failed one never
    # reached AIRE's memory, so the next attempt must still fold the history.
    await aire_topic.mark_answered(casita, claim.topic_id, state.topic)
    usage = result.usage or {}
    if model_diverged(model, result.model):
        log.warning(
            "aire_route_model_not_honoured",
            casita=casita,
            requested_model=model,
            answered_model=result.model,
            reason="AIRE binds the model at pooled-client birth; a warm session keeps the "
            "model it started with until the client is evicted (~55min idle, LRU, or a budget retire)",
        )
    log.info(
        "agent_runner_turn_complete",
        backend="aire",
        job_id=req.job_id,
        images_sent=len(images),
        documents_sent=len(documents),
        channel_id=req.channel_id,
        user_id=req.user_id,
        casita=casita,
        # The topic is part of every turn line on purpose: a casita outlives many
        # sessions now, so "which casita" no longer identifies which transcript
        # answered. Without this, a rollover would be invisible in the turn log.
        topic=claim.topic_id,
        topic_rolled_over=claim.rolled_over,
        topic_state="durable" if claim.durable else "ram",
        text_len=len(result.text),
        tool_calls=len(result.tool_calls),
        tool_names=[tc.name for tc in result.tool_calls],
        input_tokens=reported_tokens(usage, "input_tokens"),
        output_tokens=reported_tokens(usage, "output_tokens"),
        model=result.model or model,
        requested_model=model,
        elapsed_ms=int((time.monotonic() - start) * 1000),
        is_first_turn=is_first_turn,
        has_attachments=bool(req.attachments),
        **route_meta,
    )
    return TurnResponse(
        # `answer or text`, nunca `answer` a secas. AIRE parte la prosa del turno
        # en dos: todo lo que el modelo dijo, y lo que dijo DESPUÉS de su última
        # tool call. Lo primero incluye su razonamiento en voz alta camino a la
        # herramienta, pegado a la respuesta porque el join de AIRE no lleva
        # separador — así llegó "Task tracking not needed — single-turn action.
        # Proceeding to soft-delete fact 73.Hecho, amix" a #general delante de
        # dos personas (2026-09-09; seis casos en toda la historia del canal).
        # El fallback es obligatorio: un turno puede terminar EN una tool call
        # sin decir nada después, y ahí `answer` viene vacío. Nadie se queda
        # mudo por evitar una fuga.
        text=(getattr(result, "answer", "") or result.text),
        session_uuid=result.session_id,
        input_tokens=reported_tokens(usage, "input_tokens"),
        output_tokens=reported_tokens(usage, "output_tokens"),
        model=result.model or model,
        stop_reason="end_turn",
        tool_calls=[{"name": tc.name, "input_keys": list((tc.input or {}).keys())} for tc in result.tool_calls],
    )


def reported_tokens(usage: dict | None, key: str) -> int | None:
    """A token count AIRE actually reported, or None when it reported none.

    Coercing an absent count to 0 turned "unknown" into an ACCUSATION: the
    gateway's zero-generation guard reads an explicit ``output_tokens == 0``
    under real text as prose no model wrote, and degrades the turn to "…". On
    2026-09-03 every one of Insult's answers on a budget-cut AIRE turn (the SDK
    zeroes the result's usage on ``error_max_budget_usd``) died exactly there —
    eight in two days, all to Alex, while every log line stayed green. Unknown
    travels as None; only a count the backend stated is a number.
    """
    value = (usage or {}).get(key)
    return int(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def model_diverged(requested: str | None, answered: str | None) -> bool:
    """Did AIRE answer with a model this turn did not ask for?

    It legitimately can. AIRE binds the whole ``TurnSpec`` (mode, tools, model)
    when the session's POOLED CLIENT is born and never rebinds it for a live
    session (verified in aire-server ``engine/core.py::_client_for``: options are
    built only on a pool miss). This runner routes a model PER TURN
    (``routing/``), so on a warm session every later route is a request AIRE
    ignores — and a client stays warm for ~55 min (``AIRE_POOL_IDLE_S=3300``).

    Silence there would be the 2026-06-14 class again: a capability quietly not
    happening. Names are compared by prefix because the request carries an alias
    (``claude-sonnet-4-6``) and the answer carries the dated build.
    """
    if not requested or not answered:
        return False
    return not (answered.startswith(requested) or requested.startswith(answered))


def judge_casita_for(persona_id: str | None, system_prompt: str) -> str:
    """The judge's utility casita: ``{persona}-judge-{sha256(prompt)}``.

    The prompt's digest is part of the NAME on purpose, and it is what makes the
    judge safe at ANY concurrency. AIRE's door carries no per-turn system prompt
    — the only way to install one is ``/init`` on the casita — so a casita shared
    by two judges is a shared, overwritable prompt surface: judge B's ``/init``
    lands while judge A is mid-turn, and A then answers under B's instructions
    and returns something that looks perfectly fine. That was hidden only by
    ``JUDGE_MAX_CONCURRENCY`` defaulting to 1, i.e. a knob whose safety silently
    depended on which backend was serving — on the local path each judge is an
    isolated subprocess carrying its own prompt, so raising it there is safe.

    Keying by the digest makes the crossing STRUCTURALLY impossible: same casita
    ⟺ byte-identical prompt (so a concurrent ``/init`` writes the same bytes),
    and any different prompt is a different casita. No lock, so judges still run
    in parallel — which is the whole point of the knob.

    Bounded, unlike a per-call name: judge system prompts are ``.md`` files
    (``persona_core/prompts_md/``) templated with at most a persona name, and
    all per-user material rides the USER message. So the casita count is
    "distinct judge prompts times personas" — a handful, stable for the life of the
    droplet — instead of one directory per background fact extraction. AIRE has
    a broom for its tables but NOT for casitas, and a casita is a directory on a
    458 MB box, so unbounded creation would be its own defect (an AIRE-side gap
    named in the stage-2 backlog).
    """
    digest = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:32]
    return f"{base_persona_id(persona_id)}-judge-{digest}"[:_NAME_MAX]


def judge_backend_for(casita: str) -> AIREBackend:
    """A utility-casita client: mode=complete (no builtins, no agentic loop —
    the raw-API substitute), no registry tools, no per-turn casita override."""
    backend = _judge_backends.get(casita)
    if backend is None:
        backend = AIREBackend(project=casita, default_mode="complete", timeout=config.TURN_TIMEOUT_S)
        _judge_backends[casita] = backend
    return backend


async def judge_via_aire(req: JudgeRequest) -> JudgeResponse:
    """One judge call through AIRE: a mode=complete turn in the utility casita
    ``{persona_id}-judge-{prompt digest}``, throwaway session per call (one-shot,
    like today's fresh subprocess — the model per call is honoured because a
    fresh session means a fresh pooled client on AIRE's side).

    The caller's system prompt becomes the casita's prompt via ``/init``, and the
    casita is NAMED after that prompt so two differing prompts can never share
    one surface — see ``judge_casita_for``. The judge semaphore in api/judge.py
    is a throughput gate (it keeps a consolidator burst off AIRE's 2 RAM slots),
    NOT what keeps prompts apart."""
    model = req.model or config.JUDGE_DEFAULT_MODEL
    casita = judge_casita_for(req.persona_id, req.system_prompt)
    images, documents, dropped = refs_from_attachments(req.attachments)
    if dropped:
        log.warning(
            "aire_route_judge_attachments_dropped", dropped=dropped, forwarded=len(images), documents=len(documents)
        )
    backend = judge_backend_for(casita)
    try:
        result = await backend.run_turn(
            system_prompt=req.system_prompt,
            user_message=req.user_text,
            mcp_servers=[],
            tool_policy=_default_policy,
            model=model,
            session_id=None,
            images=images or None,
            documents=documents or None,
        )
    except BackendError as exc:
        log.error("aire_route_judge_failed", casita=casita, error=str(exc)[:300])
        raise HTTPException(500, f"judge call failed: {str(exc)[:200]}") from exc
    usage = result.usage or {}
    return JudgeResponse(
        text=result.text,
        model=result.model or model,
        stop_reason="end_turn",
        input_tokens=int(usage.get("input_tokens", 0) or 0),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
    )


async def reset_channel(channel_id: str) -> dict:
    """Force a fresh AIRE session for EVERY persona's casita in a channel — the
    AIRE-route successor of force-closing the channel's pooled SDK clients.

    A poisoned belief now lives in the AIRE session's transcript, and the
    session is the TOPIC: dropping the channel's durable topic rows makes each
    casita's next claim mint a fresh topic (new AIRE session, history folded
    anew). The RAM mirrors are cleared under each casita's lock so the
    Postgres-is-down fallback cannot resurrect the old topic; the abandoned
    transcripts stay in AIRE's tables until its sweep — unreferenced.
    """
    cleaned = _NAME_UNSAFE.sub("", channel_id) or "unknown"
    dropped = await aire_topic.reset_channel(cleaned)
    suffix = f"-{cleaned}"
    ram_cleared: list[str] = []
    for casita, state in list(_casita_state.items()):
        if casita.endswith(suffix):
            async with state.lock:
                state.topic = aire_topic.TopicMemory()
            ram_cleared.append(casita)
    return {
        # None ⇔ Postgres unreachable: the reset held only in RAM and a restart
        # loses it. Reported, never silently equated with a durable one.
        "durable": dropped is not None,
        "casitas": sorted(set(dropped or []) | set(ram_cleared)),
    }
