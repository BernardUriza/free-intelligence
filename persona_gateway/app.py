"""Process bootstrap — shared deps, the /invite server, and the lifecycle.

`python -m persona_gateway run` lands here: build the deps every persona-bot
shares (one MemoryStore + one AgentRunnerClient + optional susurro TTS/STT),
bind the /invite + /health port BEFORE anything slow (the ActivationFailed
root fix — bind → connect → login), then supervise each persona's Discord
session so one death never tears down the siblings.

The boot-resilience regression suite (`tests/core/test_gateway_boot_resilience.py`)
monkeypatches these names on THIS module and drives `_main` directly.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import time

import discord
import structlog

from khimeras_shared.memory import MemoryStore
from khimeras_shared.persona import PersonaRuntimeConfig
from khimeras_shared.runner.agent_client import AgentRunnerClient
from khimeras_shared.runner.judge_client import RunnerJudgeClient
from khimeras_shared.stt import build_susurro_stt_client
from khimeras_shared.tts import build_susurro_tts_client
from persona_gateway.boot import GatewayBootState
from persona_gateway.config import CONFIG
from persona_gateway.drain import TurnGate
from persona_gateway.gateway import PersonaClient
from shared.personas import gateway_personas

log = structlog.get_logger()

# Bind timing for the /invite HTTP server (external protocol contract, not a knob).
BIND_TIMEOUT_SECONDS = 15.0  # well under the ACA StartUp probe's failure budget
BIND_POLL_SECONDS = 0.05


def _build_shared() -> tuple[
    MemoryStore,
    AgentRunnerClient,
    object | None,
    object | None,
    int,
    str,
    RunnerJudgeClient,
]:
    """Construct the deps shared by all persona-bots (same wiring as Insult).

    Also builds the susurro TTS client so each persona can speak its own 🔊 audio.
    TTS is OPTIONAL — when SUSURRO_KEY is unset the client is None and voice is
    simply off. The `/invite` bearer token (GATEWAY_INVITE_TOKEN) is the same
    secret the legacy alice-bot endpoint used. The last element is the one-shot
    judge client (runner /v1/judge) that drives the automatic fact-extraction
    backstop — same runner URL + token as the turn client, a different endpoint.
    """
    config = PersonaRuntimeConfig.from_env()

    memory = MemoryStore(config.postgres_url.get_secret_value())
    runner_url = config.persona_runner_url
    runner_token = config.persona_runner_token.get_secret_value()
    if not (runner_url and runner_token):
        raise RuntimeError("persona gateway requires PERSONA_RUNNER_URL + token")
    # first_turn_timeout_s=240 (vs the 120 default): a sibling's FIRST turn — cold
    # session + curated facts + guidance — measured 134.5s in prod. The 120s
    # default read-timeout hung up 14s before the runner finished; the user got
    # the "…" fallback while a complete reply died unread.
    agent_client = AgentRunnerClient(
        runner_url=runner_url, runner_token=runner_token, timeout_s=CONFIG.first_turn_timeout_s
    )
    judge_client = RunnerJudgeClient(runner_url=runner_url, token=runner_token)

    tts_client = build_susurro_tts_client(base_url=CONFIG.susurro_url, api_key=CONFIG.susurro_key)
    # STT on the SAME susurro creds, used ONLY for DM voice notes — the one
    # surface the host cannot hear (see `MessageIngest.dm_voice_transcript`).
    stt_client = build_susurro_stt_client(base_url=CONFIG.susurro_url, api_key=CONFIG.susurro_key)
    log.info(
        "persona_gateway_tts_configured",
        enabled=tts_client is not None,
        dm_stt_enabled=stt_client is not None,
        auto_tts_min_chars=CONFIG.auto_tts_min_chars,
    )
    invite_token = config.gateway_invite_token.get_secret_value()
    return memory, agent_client, tts_client, stt_client, CONFIG.auto_tts_min_chars, invite_token, judge_client


def _serve_invite_api(
    personas: dict[str, PersonaClient],
    invite_token: str,
    boot: GatewayBootState,
    *,
    capture_signals: bool = True,
    memory=None,
):
    """Return `(server, serve_coro)` for the ported /invite endpoint.

    Port 8788 mirrors the legacy alice-bot so the Container App ingress targetPort
    is unchanged. Always served (even with no token) so the /health probe answers;
    /invite itself fail-closes (503) when the token is unset.

    `capture_signals=False` le quita a uvicorn su handler de SIGTERM porque el
    proceso ya instaló el suyo: uvicorn usa `signal.signal`, así que el último en
    instalarse gana y dos dueños de la misma señal es un dueño indefinido. Cuando
    el gateway toma la señal, apaga el turno de uvicorn y le pide salir con
    `should_exit` DESPUÉS del drenaje — que es cuando ya no le queda ningún
    `/invite?wait` en vuelo. Si el gateway NO logra instalar el suyo, esto queda
    en True y el comportamiento es exactamente el de hoy.
    """
    import uvicorn

    from persona_gateway.invite_server import build_invite_app

    class _SignallessServer(uvicorn.Server):
        # uvicorn.Config has no signal switch; Server.serve() wraps _serve in this.
        @contextlib.contextmanager
        def capture_signals(self):
            yield

    app = build_invite_app(personas, invite_token, boot, memory=memory)
    server_cls = uvicorn.Server if capture_signals else _SignallessServer
    server = server_cls(
        uvicorn.Config(
            app,
            host="0.0.0.0",  # noqa: S104  # nosec B104 — Container App ingress requires bind-all; restrict via firewall/CIDR upstream
            port=8788,
            log_level="warning",
        )
    )
    log.info("persona_gateway_invite_api_starting", port=8788, token_configured=bool(invite_token))
    return server, server.serve()


class ShutdownController:
    """SIGTERM → cerrar la puerta, dejar aterrizar lo vivo, y recién ahí morir.

    Es el dueño de la señal cuando logra instalarse. Todo lo que hace está
    envuelto en fail-safe por una razón concreta: la falla que este objeto
    previene (turnos cortados a media pipeline) es MUCHO más barata que la que
    podría introducir (un proceso que no cierra). Por eso cualquier excepción del
    drenaje se loguea y se sigue al cierre, y una segunda señal devuelve el
    handler por default y mata sin preguntar.
    """

    def __init__(
        self,
        gate: TurnGate,
        personas: dict[str, PersonaClient],
        timeout_s: float,
        boot: GatewayBootState | None = None,
    ) -> None:
        self.gate = gate
        self.personas = personas
        self.timeout_s = timeout_s
        self.boot = boot
        self.server = None  # el servidor uvicorn, cableado después de construirlo
        self.turn_tickets = None  # el registro de boletos del /invite, para soltar sus filas
        self.started = False
        self._task: asyncio.Task[None] | None = None

    def __call__(self, sig: signal.Signals) -> None:
        """Handler síncrono del loop: agenda el drenaje, no lo corre aquí."""
        if self.started:
            # Un SIGTERM repetido NO es "ya, mátalo": es la plataforma mandando
            # la misma orden otra vez. El 2026-09-19 llegaron DOS a 0.1 ms de
            # distancia y el segundo mató un turno vivo antes de que el drenaje
            # corriera. Mismo criterio que uvicorn: solo un SEGUNDO SIGINT
            # (Ctrl+C dos veces, un humano insistiendo) fuerza. Un drenaje
            # colgado no queda inmortal — la plataforma manda SIGKILL al vencer
            # el grace period.
            if sig is not signal.SIGINT:
                log.warning("persona_gateway_shutdown_signal_repeat", signal=sig.name, inflight=self.gate.inflight)
                return
            log.warning("persona_gateway_shutdown_forced", signal=sig.name)
            with contextlib.suppress(Exception):
                signal.signal(sig, signal.SIG_DFL)
                signal.raise_signal(sig)
            return
        self.started = True
        log.info("persona_gateway_shutdown_signal", signal=sig.name, inflight=self.gate.inflight)
        self._task = asyncio.create_task(self.run(), name="gateway-drain")

    async def run(self) -> None:
        try:
            self.gate.close()
            if self.boot is not None:
                self.boot.mark_stopping()
            log.info(
                "persona_gateway_drain_started",
                inflight=self.gate.inflight,
                turns=self.gate.inflight_labels,
                timeout_s=self.timeout_s,
            )
            abandoned = await self.gate.drain(self.timeout_s)
            if abandoned:
                # El tope venció con gente adentro. Se cierra igual — pero
                # contado: un abandono silencioso es peor que uno contado.
                log.error(
                    "persona_gateway_drain_abandoned",
                    abandoned=len(abandoned),
                    turns=abandoned,
                    timeout_s=self.timeout_s,
                )
            else:
                log.info("persona_gateway_drain_complete", timeout_s=self.timeout_s)
        except Exception:
            log.exception("persona_gateway_drain_crashed")
        finally:
            await self._close_everything()

    async def _close_everything(self) -> None:
        """Cierre real. Uvicorn primero (ya no le queda nada en vuelo tras el
        drenaje), y después cada sesión de Discord, aisladas entre sí."""
        if self.turn_tickets is not None:
            # Los boletos que el drenaje abandonó se sueltan en su fila para que
            # la réplica sucesora los reanude sin esperar a que venza el latido.
            with contextlib.suppress(Exception):
                await self.turn_tickets.release_open()
        if self.server is not None:
            with contextlib.suppress(Exception):
                self.server.should_exit = True
        for persona_id, client in self.personas.items():
            try:
                await client.close()
            except Exception:
                log.warning(
                    "persona_gateway_close_failed",
                    persona_id=persona_id,
                    exc_info=True,
                )


def install_shutdown_handler(controller: ShutdownController) -> bool:
    """Instala el handler en el loop. Devuelve si se pudo (fail-safe: si no, el
    llamador deja que uvicorn conserve los suyos y todo queda como hoy)."""
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, controller, sig)
    except Exception:
        # A propósito ancho: NotImplementedError, RuntimeError, ValueError y lo
        # que traiga la plataforma. No poder tomar la señal es exactamente el
        # caso en que hay que devolvérsela a uvicorn, no morirse.
        log.warning("persona_gateway_signal_handler_unavailable", exc_info=True)
        return False
    log.info("persona_gateway_shutdown_handler_installed", drain_timeout_s=controller.timeout_s)
    return True


async def _wait_until_bound(server, timeout: float = BIND_TIMEOUT_SECONDS) -> bool:
    """Block until uvicorn is actually listening, not merely scheduled.

    `asyncio.create_task(server.serve())` yields a task, not a bound socket. Every
    subsequent await — Postgres, Discord login — could otherwise run first and hang
    with port 8788 still closed, which is precisely what the ACA StartUp probe
    punishes. `server.started` flips only after the socket accepts.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if getattr(server, "started", False):
            return True
        await asyncio.sleep(BIND_POLL_SECONDS)
    log.error("persona_gateway_bind_timeout", port=8788, timeout_s=timeout)
    return False


async def _check_corpus_embed(personas: dict[str, PersonaClient]) -> None:
    """Boot-time liveness probe for the per-persona RAG corpus (finding #2).

    A corpus retrieval embeds the query at runtime via Azure OpenAI. When those
    creds are absent / rotated / point at a dead deployment, `embed_text` swallows
    the failure and returns None — indistinguishable from "no relevant hit", so a
    corpus-wide outage looks exactly like an off-topic turn and NOBODY notices the
    persona lost its library (the 2026-07-16 incident: the gateway shipped with no
    AZURE_OPENAI_* creds and every corpus turn silently degraded to bare model
    knowledge). This probe makes the outage LOUD at boot instead of invisible.

    Off the port-bind critical path (mirrors `_connect_memory`): a probe failure
    logs ERROR but never kills the process — the personas still serve, just
    without their corpus. Skipped entirely when no live persona has a corpus.
    """
    has_corpus = any(getattr(getattr(p, "persona", None), "corpus_namespace", None) for p in personas.values())
    if not has_corpus:
        return
    try:
        from khimeras_shared.corpus.pg_rag import embed_text

        vec = await embed_text("corpus embed boot healthcheck")
    except Exception:
        log.exception("persona_gateway_corpus_embed_check_crashed")
        return
    if vec is None:
        log.error(
            "persona_gateway_corpus_embed_unavailable",
            note="RAG corpus retrieval is DEAD — embed_text returned None; check AZURE_OPENAI_ENDPOINT/KEY + deployment",
        )
    else:
        log.info("persona_gateway_corpus_embed_ok", dim=len(vec))


async def _connect_memory(memory, boot: GatewayBootState) -> None:
    """Connect Postgres off the probe's critical path.

    A cold Postgres must never keep port 8788 from binding: the ACA StartUp probe
    kills the replica, the restart burns another Discord IDENTIFY, and the
    crashloop feeds itself. `MemoryStore._ensure_connection` reconnects before
    every operation, so a boot-time failure degrades rather than kills.
    """
    try:
        await memory.connect()
    except Exception as exc:
        log.exception("persona_gateway_db_connect_failed", error=type(exc).__name__)
        return
    boot.mark_db_connected()


async def _supervise_persona(persona_id: str, coro, boot: GatewayBootState) -> None:
    """Await one persona's Discord session, isolating its death from its siblings.

    `Client.start` only returns when the session ends. Whatever it raises — a
    throttled IDENTIFY, a revoked token, a gateway hang — belongs to THIS persona
    and must not tear down the process: the other bots keep serving, `/invite`
    keeps answering, and `/health` reports the loss.
    """
    try:
        await coro
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.exception("persona_gateway_persona_failed", persona_id=persona_id, error=type(exc).__name__)
    else:
        # Una salida DURANTE el drenaje es la salida esperada, no una pérdida.
        if boot.stopping:
            log.info("persona_gateway_persona_drained", persona_id=persona_id)
        else:
            log.error("persona_gateway_persona_exited", persona_id=persona_id)
    boot.mark_persona_down(persona_id)


async def _main() -> None:
    memory, agent_client, tts_client, stt_client, auto_tts_min_chars, invite_token, judge_client = _build_shared()

    intents = discord.Intents.default()
    intents.message_content = True

    # Una sola puerta para las N personas: el SIGTERM llega una vez al proceso.
    gate = TurnGate()

    personas: dict[str, PersonaClient] = {}
    tokens: dict[str, str] = {}
    for persona in gateway_personas():
        token = os.environ.get(persona.token_env, "").strip()
        if not token:
            log.warning("persona_gateway_no_token", persona_id=persona.persona_id, env=persona.token_env)
            continue
        personas[persona.persona_id] = PersonaClient(
            persona,
            memory,
            agent_client,
            intents=intents,
            tts_client=tts_client,
            stt_client=stt_client,
            auto_tts_min_chars=auto_tts_min_chars,
            judge_client=judge_client,
            gate=gate,
        )
        tokens[persona.persona_id] = token

    if not personas:
        log.error("persona_gateway_nothing_to_start", note="no persona token configured")
        return

    # Every client now exists, so each can reach its siblings: this is what makes
    # a persona's `[INVITE:]` actually summon one. Without it the marker is only
    # stripped and the sibling never arrives — the state prod was in from the
    # 2026-07-14 purge until 2026-08-06.
    for client in personas.values():
        client.bind_siblings(personas)

    boot = GatewayBootState()

    # El handler se instala ANTES de construir el servidor porque decide quién
    # es dueño de SIGTERM: si el gateway lo toma, uvicorn no debe tomarlo (los
    # dos usan `signal.signal` y el último gana). Si no se pudo instalar, uvicorn
    # conserva los suyos y el cierre es el de siempre.
    shutdown = ShutdownController(gate, personas, CONFIG.drain_timeout_s, boot)
    owns_signals = install_shutdown_handler(shutdown)

    # The HTTP server binds BEFORE Postgres and before any Discord login, so the
    # StartUp probe answers as soon as the process is alive. Until a persona
    # finishes on_ready, /health reports serving=false — honestly.
    server, serve_coro = _serve_invite_api(
        personas, invite_token, boot, capture_signals=not owns_signals, memory=memory
    )
    shutdown.server = server
    invite_app = getattr(getattr(server, "config", None), "app", None)
    shutdown.turn_tickets = getattr(getattr(invite_app, "state", None), "turn_tickets", None)
    api_task = asyncio.create_task(serve_coro, name="invite-api")
    if await _wait_until_bound(server):
        log.info("persona_gateway_api_bound", port=8788)

    await _connect_memory(memory, boot)
    await _check_corpus_embed(personas)
    resume_task = asyncio.create_task(_resume_stale_invites(invite_app, personas), name="invite-resume")

    persona_tasks = [
        asyncio.create_task(
            _supervise_persona(persona_id, client.start(tokens[persona_id]), boot),
            name=f"persona:{persona_id}",
        )
        for persona_id, client in personas.items()
    ]
    for persona_id in personas:
        log.info("persona_gateway_starting", persona_id=persona_id)

    try:
        await asyncio.gather(*persona_tasks)
        if boot.stopping:
            log.info("persona_gateway_stopped", personas=sorted(personas))
        else:
            log.error("persona_gateway_all_personas_down", personas=sorted(personas))
    finally:
        resume_task.cancel()
        api_task.cancel()
        await asyncio.gather(api_task, resume_task, return_exceptions=True)
        await memory.close()


async def _resume_stale_invites(app, personas: dict[str, PersonaClient], *, ready_wait_s: float = 120.0) -> None:
    """Boot: en cuanto una persona esté lista, reclama los turnos huérfanos de la
    réplica anterior. Best-effort — nunca bloquea el boot ni lo tumba."""
    deadline = time.monotonic() + ready_wait_s
    while time.monotonic() < deadline and not any(getattr(c, "user", None) is not None for c in personas.values()):
        await asyncio.sleep(2.0)
    resume = getattr(getattr(app, "state", None), "resume_stale_turns", None)
    if resume is None:
        return
    try:
        await resume()
    except Exception:
        log.warning("persona_gateway_boot_resume_failed", exc_info=True)


def run() -> None:
    """CLI entrypoint: `python -m persona_gateway run`."""
    asyncio.run(_main())
