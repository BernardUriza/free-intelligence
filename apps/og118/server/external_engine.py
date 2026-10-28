"""og118 external engine proxy (ENGINE-BINDING-ADR-1, external_http_engine).

When an element binds to an external FI engine — the already-running Vultur
runner for Oxígeno, the Insult runner for Yodo — og118 does NOT run a local turn.
It hands the user text to that engine and surfaces the answer. The engine owns
its own persona (selected by `persona_id`) and threads context in a long-lived
session keyed by `channel_id` — its `session_uuid` field is accepted for schema
compat but IGNORED (persona_runner v3.9.31+). So og118 sends the og118
conversation id AS `channel_id` (one og118 thread ⇒ one engine session; a shared
constant would pool every user's conversations into ONE Claude session —
cross-account context bleed) and replays the capped client history so the engine
can seed a FRESH session (reaped idle slot, replica restart, element switched
mid-conversation) with the thread it never saw.

OG118-EXTERNAL-TURN-1 (2026-10-15): the turn rides the engine's TICKET, never one
long request. `POST /v1/turn/jobs` with a `job_id` derived from the turn (so the
client's retry of the same text collides into the same job: one run, one memory
write); `GET /v1/turn/jobs/{id}/events` streams each `tool_call` the engine makes
as it makes it (the glass-box steps fi-glass already paints); `GET /v1/turn/jobs/{id}`
long-polls the result (≤50s per request, well under the 240s ingress cap). Text
still arrives whole in `result` — the engine strips the persona's markers from the
final text, so only the verbs are live for now.

The live stream waits `LIVE_WAIT_S`. Past it, og118 releases the client with a
`deferred` frame WITHOUT abandoning the ticket: the poll goes on here and the
answer lands in the conversation record through `deliver_late`
(`ConversationStore.append_late_turn`), where the client's 15s sync paints it.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx

from conversations import utc_now_iso

log = logging.getLogger("og118.external_engine")

RUNNER_URL = os.getenv("OG118_EXTERNAL_RUNNER_URL", "").rstrip("/")
RUNNER_TOKEN = os.getenv("OG118_EXTERNAL_RUNNER_TOKEN", "")
# Live wait = the engine's TURN_TIMEOUT_S (90s) + the cold start that runs BEFORE
# its clock starts (measured 2026-10-15: 26s boot + 8s pipeline + 12s embeddings).
ENGINE_TURN_CEILING_S = 90.0
ENGINE_COLD_START_S = 60.0
LIVE_WAIT_S = ENGINE_TURN_CEILING_S + ENGINE_COLD_START_S
# Per-request reads: the runner's long-poll ceiling (persona_core.tickets.MAX_WAIT_S)
# and its events stream, which pings every 15s. Nothing here approaches the ingress' 240s.
POLL_WAIT_S = 50.0
EVENTS_READ_S = 60.0
JOB_DEADLINE_S = 600.0
POLL_TRANSIENT_RETRIES = 3
_TIMEOUT = httpx.Timeout(POLL_WAIT_S + 10.0, connect=10.0)
_EVENTS_TIMEOUT = httpx.Timeout(EVENTS_READ_S, connect=10.0)

LateDelivery = Callable[[dict], Awaitable[None]]
_LATE_TASKS: set[asyncio.Task] = set()

# Same caps fi_runner applies to client-replayed history on the local path
# (Runner.client_history_max_messages/_chars). The external path bypasses
# fi_runner, so the cap is enforced here before the payload leaves og118.
HISTORY_MAX_MESSAGES = 20
HISTORY_MAX_CHARS = 16_000
_HISTORY_ROLES = frozenset({"user", "assistant"})


def is_configured() -> bool:
    return bool(RUNNER_URL and RUNNER_TOKEN)


def turn_job_id(session_uuid: str | None, user_text: str, history: list[dict] | None) -> str:
    """The ticket id of THIS turn: the thread, its position and the text. A retry
    of the same send maps to the same job — the runner reuses the ticket instead
    of running the turn twice. Without a thread there is nothing to retry into."""
    if not session_uuid:
        return uuid.uuid4().hex
    seed = f"{session_uuid}\n{len(history or [])}\n{user_text}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def cap_history(history: list[dict] | None) -> list[dict]:
    """Bound the replayed thread the way fi_runner.sanitize_history does on the
    local path: role-allowlisted, newest-first budget, chronological output."""
    if not history:
        return []
    kept: list[dict] = []
    total = 0
    for msg in reversed(history[-HISTORY_MAX_MESSAGES:]):
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role not in _HISTORY_ROLES or not content:
            continue
        if total + len(content) > HISTORY_MAX_CHARS:
            break
        kept.append({"role": role, "content": content})
        total += len(content)
    kept.reverse()
    return kept


def render_outbound(data: dict) -> str:
    """The part of the engine's turn that IS message content: the text, plus the
    persona's GIFs as markdown images the chat renders inline.

    Since server-bot F5 the engine returns the `OutboundTurn` it assembled, not
    just its text. A GIF (from the persona's own catalog) is content, so it goes
    in the body. A reaction is NOT content — it is a gesture on the message, the
    way Discord shows it under the bubble — so it never gets folded in here: it
    rides the `result` event as `reactions` (see `outbound_reactions`) and
    fi-glass renders it as chips. An engine predating F5 has neither field and
    renders exactly as before.
    """
    text = str(data.get("text", "")).strip()
    gifs = [str(u).strip() for u in (data.get("gif_urls") or []) if str(u).strip().startswith("https://")]
    parts: list[str] = []
    if text:
        parts.append(text)
    parts.extend(f"![gif]({url})" for url in gifs)
    return "\n\n".join(parts)


def outbound_reactions(data: dict) -> list[str]:
    """The emoji the persona reacted with, as the engine reported them."""
    return [str(r).strip() for r in (data.get("reactions") or []) if str(r).strip()]


def outbound_events(data: dict) -> list[dict]:
    """The engine's finished turn as og118 stream events: `text` + `result`, or a
    single secret-free `error` when it came back empty."""
    text = render_outbound(data)
    reactions = outbound_reactions(data)
    if not text and not reactions:
        # server-bot F5 names why a turn came back empty ("markers_only",
        # "brain_empty"); an engine predating it says nothing.
        reason = str(data.get("empty_reason") or "").strip()
        detail = f" ({reason})" if reason else ""
        return [{"type": "error", "message": f"external engine returned an empty answer{detail}"}]
    events: list[dict] = []
    if text:
        events.append({"type": "text", "text": text})
    # The engine reports the model it ran (e.g. claude-sonnet-4-6). Settle the turn
    # with a `result` so that provenance reaches the client the same way the local
    # path delivers it. The text is repeated (the reducer replaces, never appends);
    # the persona's reactions ride here structured: a reaction-only turn is a
    # settled turn with empty text and a gesture, not an error.
    result: dict = {"text": text, "model": data.get("model")}
    if reactions:
        result["reactions"] = reactions
    events.append({"type": "result", "result": result})
    return events


def late_message(events: list[dict]) -> dict:
    """The engine's late turn as the assistant message the thread stores: the
    answer with its reactions, or a visible note naming why there is none."""
    result = next((e for e in events if e.get("type") == "result"), None)
    if result is None:
        error = next((e for e in events if e.get("type") == "error"), None)
        reason = error["message"] if error else "sin respuesta"
        return {
            "role": "assistant",
            "content": (
                f"og118: el motor de este elemento no entregó respuesta ({reason}). "
                "Vuelve a mandar el mensaje."
            ),
            "timestamp": utc_now_iso(),
        }
    payload = result.get("result") or {}
    message: dict = {
        "role": "assistant",
        "content": str(payload.get("text") or ""),
        "timestamp": utc_now_iso(),
    }
    reactions = list(payload.get("reactions") or [])
    if reactions:
        message["reactions"] = reactions
    return message


def _error(message: str) -> dict:
    return {"type": "error", "message": message}


async def _submit(client: httpx.AsyncClient, payload: dict, headers: dict) -> str | dict:
    """Open the ticket. Returns the job id, or the one `error` event to emit."""
    try:
        resp = await client.post(f"{RUNNER_URL}/v1/turn/jobs", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return _error(f"external engine unreachable: {type(exc).__name__}")
    if resp.status_code != 202:
        return _error(f"external engine returned {resp.status_code}")
    try:
        job_id = str(resp.json().get("job_id") or "")
    except ValueError:
        return _error("external engine returned a non-JSON body")
    return job_id or _error("external engine accepted the turn without a job_id")


async def _sse_blocks(lines: AsyncIterator[str]) -> AsyncIterator[tuple[int | None, str | None, dict]]:
    event_id: int | None = None
    event: str | None = None
    data: list[str] = []
    async for raw in lines:
        line = raw.rstrip("\r")
        if line == "":
            if data:
                try:
                    parsed = json.loads("\n".join(data))
                except ValueError:
                    parsed = {}
                yield event_id, event, parsed if isinstance(parsed, dict) else {}
            event_id, event, data = None, None, []
        elif line.startswith("id:"):
            value = line[3:].strip()
            event_id = int(value) if value.isdigit() else event_id
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())


_LIVE_FRAMES = frozenset({"tool_call", "text"})


async def _tail_events(client: httpx.AsyncClient, job_url: str, headers: dict, frames: asyncio.Queue) -> None:
    """Follow the ticket's event log, reconnecting from the last id, until `done`.
    `tool_call` and `text` frames are forwarded live; the result travels by the poll."""
    cursor = 0
    while True:
        try:
            async with client.stream(
                "GET", f"{job_url}/events", headers={**headers, "Last-Event-ID": str(cursor)}, timeout=_EVENTS_TIMEOUT
            ) as resp:
                if resp.status_code != 200:
                    return
                async for event_id, event, data in _sse_blocks(resp.aiter_lines()):
                    if event == "done":
                        return
                    if event_id is not None:
                        cursor = event_id
                    if data.get("type") in _LIVE_FRAMES:
                        await frames.put(data)
        except httpx.HTTPError:
            pass
        await asyncio.sleep(1.0)


async def _poll_once(client: httpx.AsyncClient, job_url: str, headers: dict) -> dict | list[dict]:
    """One long-poll of the ticket: the body, or the terminal `error` events."""
    resp = await client.get(job_url, params={"wait_s": POLL_WAIT_S}, headers=headers)
    if resp.status_code == 404:
        return [_error("external engine lost the turn (runner restarted)")]
    if resp.status_code != 200:
        return [_error(f"external engine returned {resp.status_code}")]
    try:
        body = resp.json()
    except ValueError:
        return [_error("external engine returned a non-JSON body")]
    return body if isinstance(body, dict) else [_error("external engine returned a non-JSON body")]


async def _poll_result(client: httpx.AsyncClient, job_url: str, headers: dict) -> list[dict]:
    """Ask the ticket in short requests until the turn is done (or the runner's
    own 600s deadline passes). A poll that drops is asked again; the turn lives."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + JOB_DEADLINE_S
    failures = 0
    while loop.time() < deadline:
        try:
            got = await _poll_once(client, job_url, headers)
        except httpx.HTTPError as exc:
            failures += 1
            if failures >= POLL_TRANSIENT_RETRIES:
                return [_error(f"external engine unreachable: {type(exc).__name__}")]
            await asyncio.sleep(1.0)
            continue
        failures = 0
        if isinstance(got, list):
            return got
        if got.get("status") == "done":
            return outbound_events(got.get("response") or {})
    return [_error(f"external engine did not finish within {JOB_DEADLINE_S:.0f}s")]


def _settle(events: list[dict], streamed_text: bool) -> list[dict]:
    """The ticket's final events for the live stream. When the text already
    streamed as deltas, the whole-text `text` event would be APPENDED by the
    reducer and double the answer; only `result` goes out — it replaces."""
    if not streamed_text:
        return events
    return [e for e in events if e.get("type") != "text"]


def _deliver_when_done(task: asyncio.Task, deliver_late: LateDelivery, aclose: Callable[[], Awaitable[None]]) -> None:
    async def finish() -> None:
        try:
            await deliver_late(late_message(await task))
        except Exception:
            log.exception("late external turn was not delivered")
        finally:
            await aclose()

    late = asyncio.create_task(finish())
    _LATE_TASKS.add(late)
    late.add_done_callback(_LATE_TASKS.discard)


def _payload(*, persona_id: str, user_text: str, session_uuid: str | None, user_id: str | None, history) -> dict:
    payload: dict = {
        # The engine's continuity key is channel_id (one long-lived SDK session
        # per channel — persona_runner ignores session_uuid). og118's conversation
        # id IS the channel: per-thread continuity, zero cross-user sharing.
        "channel_id": session_uuid or "0",
        "user_id": user_id or "0",
        "user_text": user_text,
        "persona_id": persona_id,
        # Which surface emitted `user_id`: the engine resolves (surface, id) to
        # its canonical principal before it reads memory (server-bot F2).
        "surface": "og118",
        "job_id": turn_job_id(session_uuid, user_text, history),
    }
    if session_uuid:
        payload["session_uuid"] = session_uuid
    # og118 has no turn pipeline of its own, so the engine runs it (server-bot
    # F3): it stores the turn, runs the guardian and grows the user's facts.
    # Only for a real person in a real conversation — a legacy-bearer caller or
    # a turn with no conversation id would pile every stranger into one memory.
    if user_id and session_uuid:
        payload["pipeline"] = "runner"
    # A probe (the element editor's "probar") stores tagged rows and grows no facts.
    if user_id and user_id.startswith("probe-"):
        payload["origin"] = "probe"
    # Replayed client history (untrusted context, never authorization — same
    # doctrine as the local path). The engine folds it only when it opens a
    # fresh session for this channel; engines predating the field ignore it.
    capped = cap_history(history)
    if capped:
        payload["history"] = capped
    return payload


async def stream_external_turn(
    *,
    persona_id: str,
    user_text: str,
    session_uuid: str | None,
    user_id: str | None,
    history: list[dict] | None = None,
    deliver_late: LateDelivery | None = None,
    live_wait_s: float = LIVE_WAIT_S,
) -> AsyncIterator[dict]:
    """Run one turn on the external engine's ticket and yield og118 stream events.

    Yields og118-native event dicts (the same shape the local runner emits, so the
    frontend hook maps them unchanged): each `tool_call` as the engine makes it
    and the answer's text as it is written (OG118-EXTERNAL-TURN-2), then `result`
    when the ticket is done (plus the whole `text` when nothing streamed). On any failure yields a single
    secret-free `error` event.

    Past `live_wait_s` the live stream ends with a single `deferred` frame (the
    client folds no bubble and shows a waiting notice) and the poll goes on;
    `deliver_late` receives the finished assistant message. Without a
    `deliver_late` (no thread to land in) the cut is an `error`."""
    if not is_configured():
        yield _error("external engine not configured (OG118_EXTERNAL_RUNNER_URL/TOKEN unset)")
        return
    headers = {"Authorization": f"Bearer {RUNNER_TOKEN}", "Content-Type": "application/json"}
    client = httpx.AsyncClient(timeout=_TIMEOUT)
    submitted = await _submit(
        client,
        _payload(persona_id=persona_id, user_text=user_text, session_uuid=session_uuid, user_id=user_id, history=history),
        headers,
    )
    if isinstance(submitted, dict):
        await client.aclose()
        yield submitted
        return
    job_url = f"{RUNNER_URL}/v1/turn/jobs/{submitted}"
    frames: asyncio.Queue = asyncio.Queue()
    tail = asyncio.create_task(_tail_events(client, job_url, headers, frames))
    result = asyncio.create_task(_poll_result(client, job_url, headers))
    detached = False
    streamed_text = False
    loop = asyncio.get_running_loop()
    deadline = loop.time() + live_wait_s
    try:
        while True:
            getter = asyncio.create_task(frames.get())
            done, _ = await asyncio.wait({getter, result}, timeout=max(0.0, deadline - loop.time()), return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                frame = getter.result()
                streamed_text = streamed_text or frame.get("type") == "text"
                yield frame
                continue
            getter.cancel()
            if result in done:
                while not frames.empty():
                    frame = frames.get_nowait()
                    streamed_text = streamed_text or frame.get("type") == "text"
                    yield frame
                for event in _settle(result.result(), streamed_text):
                    yield event
                return
            if deliver_late is None:
                yield _error(f"external engine took longer than {live_wait_s:.0f}s")
                return
            detached = True
            _deliver_when_done(result, deliver_late, client.aclose)
            yield {"type": "deferred"}
            return
    finally:
        tail.cancel()
        if not detached:
            result.cancel()
            await client.aclose()


class PersonaWriteError(RuntimeError):
    """The engine refused or could not store the persona; `status` is its HTTP code."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status


async def _persona_call(method: str, persona_id: str, body: dict | None = None) -> httpx.Response:
    if not is_configured():
        raise PersonaWriteError(503, "external engine not configured")
    headers = {"Authorization": f"Bearer {RUNNER_TOKEN}"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.request(method, f"{RUNNER_URL}/v1/personas/{persona_id}", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise PersonaWriteError(502, f"engine unreachable: {type(e).__name__}") from e
    if r.status_code not in (200, 204):
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise PersonaWriteError(r.status_code, str(detail)[:500])
    return r


async def put_persona(persona_id: str, body: dict) -> dict:
    """Write a persona to the engine (`PUT /v1/personas/{id}`); returns its version."""
    return (await _persona_call("PUT", persona_id, body)).json()


async def get_persona(persona_id: str) -> dict:
    """Read a runtime persona back from the engine: name, engine, DNA and version."""
    return (await _persona_call("GET", persona_id)).json()


async def delete_persona(persona_id: str) -> None:
    """Tombstone a runtime persona on the engine."""
    await _persona_call("DELETE", persona_id)
