"""Paridad entre los DOS caminos por los que una persona contesta un turno.

Una persona llega a hablar por dos puertas y sólo por dos:

  (A) **@mención** — `PersonaClient._handle`, disparado por `should_respond`.
  (B) **invitación** — `PersonaClient.respond_to_invite`, disparado por el
      `/invite` que manda el host (`khimeras-host`) o por el `[INVITE:]` de una
      persona hermana.

La clase de bug que este arnés cierra se llama **"el invite path olvidado"**: se
le agrega una capacidad a UNA puerta y se olvida la otra. No es teoría — está
firmado en el propio código:

- `invites.py::fetch_trigger` documenta el bug del 2026-07-14: sin mensaje
  disparador resuelto, las reacciones `[REACT:]` del path B se morían.
- el mismo docstring documenta el del 2026-07-16: un turno ruteado por el host
  sobre una imagen iba CIEGO porque los adjuntos sólo se leían en el path A.
- `turn_context.py` documenta el del 2026-07-19: guardián, reminders y relevant
  estaban cableados sólo al path A — justo el que el cutover del host acababa de
  dejar sin tráfico. El path primario corría con corpus y nada más.

Tres bugs, la misma forma, en cinco días. La cura estructural es que TODO lo
compartido viva en un solo lugar (`TurnContextBuilder` para el contexto,
`TurnRunner` para la entrega) y que las dos puertas lo atraviesen. Este archivo
lo verifica de dos maneras complementarias:

- **estructural** (AST): las dos puertas invocan el mismo conjunto de servicios
  de `self`; una capacidad nueva cableada a una sola se pone roja aquí, aunque
  nadie escriba un test de comportamiento.
- **de comportamiento**: se maneja el MISMO mensaje humano por las dos puertas y
  se afirma capacidad por capacidad que ambas la ejercen.

Las asimetrías REALES que se encontraron al escribirlo no se arreglan aquí — el
fix es del hilo principal. Quedan como `xfail(strict=True)`: rojo honesto en vez
de verde falso, y cuando alguien las arregle el strict se pone rojo pidiendo que
se retire la marca. Las asimetrías DELIBERADAS (STT del host, recepción) están
en la última sección como excepciones explícitas, para que nadie "arregle" una
paridad que no debe existir.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import inspect
import textwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from khimeras_shared.version import VERSION_TAG
from persona_gateway import gateway as gateway_module
from persona_gateway.delivery import DISCORD_LIMIT
from persona_gateway.gateway import PersonaClient
from persona_gateway.ingest import MessageIngest
from shared.personas import Persona

MENTION = "mention"
INVITE = "invite"
BOTH_PATHS = [MENTION, INVITE]

HUMAN_ID = 907264175246569543
BOT_ID = 1503983124982534284
TRIGGER_ID = 1527198401375113227
CHANNEL_ID = "1489180895264116736"

ASK = "mira este encuadre, ¿qué opinas?"
REASON = "bernard2389 pregunta por un encuadre; te toca a ti"


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = int(CHANNEL_ID)
    channel.name = "general"
    channel.send = AsyncMock(side_effect=lambda *a, **kw: SimpleNamespace(id=1))
    channel.typing = MagicMock(return_value=_Typing())
    channel.fetch_message = AsyncMock()
    return channel


def _image_attachment():
    att = MagicMock()
    att.filename = "encuadre.png"
    att.content_type = "image/png"
    att.size = 1000
    att.read = AsyncMock(return_value=b"fakepng")
    return att


def _human_message(channel, *, content: str = ASK, attachments=None, author_is_bot: bool = False):
    """El MISMO mensaje humano que las dos puertas van a procesar.

    En el path A llega como el mensaje que menciona a la persona; en el path B
    llega como el `trigger_message_id` que el host adjunta al invite. Es
    deliberadamente el mismo objeto: la única diferencia entre los caminos debe
    ser QUIÉN se lo entrega a la persona, nunca QUÉ ve la persona.
    """
    msg = MagicMock()
    msg.id = TRIGGER_ID
    msg.channel = channel
    msg.guild = SimpleNamespace(id=1)
    msg.content = content
    msg.attachments = attachments or []
    msg.flags = SimpleNamespace(voice=False)
    msg.author = SimpleNamespace(id=HUMAN_ID, display_name="bernard2389", bot=author_is_bot)
    msg.add_reaction = AsyncMock()
    return msg


def _client(reply_text: str = "Va, ese encuadre corta.") -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[{"user_name": "alex", "content": "hola", "role": "user"}])
    memory.search = AsyncMock(return_value=[{"user_name": "alex", "content": "algo viejo", "timestamp": 1.0}])
    memory.build_context = MagicMock(side_effect=lambda recent, **kw: list(recent))
    memory.search_facts_semantic = AsyncMock(return_value=[{"fact": "le importa el encuadre"}])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.append_to_message = AsyncMock(return_value=True)
    agent_client = MagicMock()

    async def _chat(*args, **kwargs):
        # Un tick real: el keepalive de typing es una task de fondo que sólo
        # alcanza a correr si la llamada al runner cede el loop, como en prod.
        await asyncio.sleep(0.01)
        return SimpleNamespace(text=reply_text, model_used="claude")

    agent_client.chat = AsyncMock(side_effect=_chat)
    client = PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())
    client._connection.user = SimpleNamespace(id=BOT_ID)
    client.judge_client = MagicMock()
    return client


async def _run(
    path: str,
    *,
    reply_text: str = "Va, ese encuadre corta.",
    content: str = ASK,
    attachments=None,
    author_is_bot: bool = False,
    gif_urls: tuple[str, ...] = (),
    corpus_block: str | None = None,
    guarded: bool = False,
    user_store_raises: bool = False,
    ingest_raises: bool = False,
    auto_tts_min_chars: int = 0,
):
    """Maneja el mismo mensaje por la puerta `path` y devuelve lo que se ejerció.

    Todos los parches se aplican IGUAL a los dos caminos: si un test ve una
    diferencia, la diferencia está en el código de producción, no en el arnés.
    """
    client = _client(reply_text)
    channel = _channel()
    message = _human_message(channel, content=content, attachments=attachments, author_is_bot=author_is_bot)
    channel.fetch_message.return_value = message
    client._turns.auto_tts_min_chars = auto_tts_min_chars

    if user_store_raises:

        async def _store(*args, **kwargs):
            if len(args) > 3 and args[3] == "user":
                raise RuntimeError("postgres se cayó a media escritura")

        client.memory.store = AsyncMock(side_effect=_store)
    if ingest_raises:
        client._ingest.attachment_blocks = AsyncMock(side_effect=RuntimeError("adjunto corrupto"))

    with contextlib.ExitStack() as stack:
        enter = stack.enter_context
        outcome = SimpleNamespace(
            client=client,
            channel=channel,
            message=message,
            guardian=enter(
                patch("persona_gateway.turn_context.guidance_for_turn", new=AsyncMock(return_value="GUIA-DEL-GUARDIAN"))
            ),
            other_people=enter(
                patch(
                    "persona_gateway.turn_context.other_people_block_for_turn",
                    new=AsyncMock(return_value="OTROS: alex…"),
                )
            ),
            corpus=enter(
                patch(
                    "persona_gateway.turn_context.build_persona_corpus_block",
                    new=AsyncMock(return_value=corpus_block),
                )
            ),
            add_reactions=enter(patch("persona_gateway.turns.add_reactions", new_callable=AsyncMock)),
            resolve_gifs=enter(patch("persona_gateway.turns.resolve_gifs", return_value=list(gif_urls))),
            persist_remembers=enter(patch("persona_gateway.markers.persist_remembers", new=AsyncMock(return_value=1))),
            spawn_facts=enter(patch.object(client, "_spawn_fact_extraction")),
            spawn_vision=enter(patch.object(client._vision, "spawn")),
            speak=enter(patch.object(client._voice, "speak", new_callable=AsyncMock)),
        )
        enter(patch.object(client, "get_channel", return_value=channel))
        if path == MENTION:
            await (client._dispatch(message) if guarded else client._handle(message))
        else:
            await (
                client.dispatch_invite(
                    channel_id=CHANNEL_ID,
                    guild_id="G1",
                    channel_name="general",
                    reason=REASON,
                    invited_by="host",
                    trigger_message_id=str(TRIGGER_ID),
                )
                if guarded
                else client.respond_to_invite(
                    channel_id=CHANNEL_ID,
                    guild_id="G1",
                    channel_name="general",
                    reason=REASON,
                    invited_by="host",
                    trigger_message_id=str(TRIGGER_ID),
                )
            )
        await asyncio.sleep(0)

    outcome.chat = client.agent_client.chat
    outcome.sent = " ".join(str(call) for call in channel.send.call_args_list)
    return outcome


def _chat_kwargs(outcome):
    return outcome.chat.await_args.kwargs


def _last_user_content(outcome):
    return outcome.chat.await_args.args[1][-1]["content"]


# --- Sección A: los seams compartidos (estructural, AST) ----------------------


def _dotted(node: ast.AST) -> str | None:
    """`self._context.build` a partir del `func` de un Call, o None."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name) or node.id != "self":
        return None
    parts.append("self")
    return ".".join(reversed(parts))


def _self_calls(func) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return {name for node in ast.walk(tree) if isinstance(node, ast.Call) and (name := _dotted(node.func)) is not None}


def _self_assignments(func) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                names.add(f"self.{target.attr}")
    return names


MENTION_ONLY_CALLS = {
    # El host es DEAF en un DM (Discord aísla el canal por bot user), así que
    # nadie más puede transcribir ahí. `.claude/rules/voice.md` lo declara la
    # ÚNICA excepción a "sólo el host transcribe"; el path B recibe las palabras
    # ya transcritas en `trigger_transcript`. Ver `test_stt_ownership_is_split_on_purpose`.
    "self._ingest.dm_voice_transcript",
}


def test_the_two_doors_call_the_same_services():
    """El catcher genérico de "el invite path olvidado".

    Si alguien cablea un servicio nuevo (`self._loquesea.x()`) a una sola puerta,
    esto se pone rojo el mismo día — sin que nadie tenga que acordarse de
    escribir el test de comportamiento correspondiente. Las diferencias
    legítimas se declaran arriba, con su razón.
    """
    mention = _self_calls(PersonaClient._handle)
    invite = _self_calls(PersonaClient.respond_to_invite)

    only_mention = mention - invite - MENTION_ONLY_CALLS
    only_invite = invite - mention
    assert not only_mention, f"capacidades cableadas SÓLO al path de @mención: {sorted(only_mention)}"
    assert not only_invite, f"capacidades cableadas SÓLO al path de invite: {sorted(only_invite)}"


def test_the_two_doors_stamp_the_same_state():
    """La REGLA general: todo estado que una puerta estampe, la otra lo estampa.

    Nació roja el 2026-08-06 (`_handle` estampaba `last_message_seen` y
    `respond_to_invite` no) y se puso verde el mismo día. Se queda para que la
    PRÓXIMA señal de liveness no nazca coja: el defecto no fue el sello que
    faltaba, fue que nadie comparaba las dos puertas.
    """
    mention = _self_assignments(PersonaClient._handle)
    invite = _self_assignments(PersonaClient.respond_to_invite)
    assert mention == invite, f"estado estampado por una sola puerta: {sorted(mention ^ invite)}"


@pytest.mark.parametrize("seam", ["self._context.build", "self._run_and_deliver"])
def test_both_doors_go_through_the_single_seam(seam: str):
    """Los dos embudos que hacen barata la paridad: `TurnContextBuilder` arma el
    contexto y `TurnRunner` entrega. Mientras las dos puertas los atraviesen,
    toda capacidad nueva que viva ahí nace con paridad gratis. Una puerta que se
    ensamble el turno a mano es exactamente la deriva del 2026-07-19."""
    assert seam in _self_calls(PersonaClient._handle), f"el path de @mención dejó de pasar por {seam}"
    assert seam in _self_calls(PersonaClient.respond_to_invite), f"el path de invite dejó de pasar por {seam}"


@pytest.mark.parametrize(
    "owned_by_the_turn_runner",
    ["add_reactions(", "send_chunked(", "resolve_gifs(", "parse_reactions(", "should_auto_speak("],
)
def test_delivery_capabilities_are_not_duplicated_in_the_gateway(owned_by_the_turn_runner: str):
    """La entrega (reacciones, chunking, GIFs, TTS) vive en UN solo módulo.

    Una copia en `gateway.py` volvería a hacer que "arreglarlo" signifique
    arreglarlo dos veces — y la segunda se olvida. Art. 6 al nivel del diff.
    """
    assert owned_by_the_turn_runner not in inspect.getsource(gateway_module), (
        f"{owned_by_the_turn_runner} volvió a duplicarse fuera de TurnRunner"
    )


# --- Sección B: paridad de capacidades (comportamiento) -----------------------


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_the_image_reaches_the_runner(path: str):
    """El bug del 2026-07-16: un turno ruteado por el host sobre una foto iba
    ciego porque los adjuntos sólo se leían en el path de @mención."""
    outcome = await _run(path, attachments=[_image_attachment()])
    content = _last_user_content(outcome)
    assert isinstance(content, list), f"[{path}] el turno con imagen se mandó como texto plano"
    assert any(block.get("type") == "image" for block in content), f"[{path}] la imagen no llegó al runner"


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_the_guardian_runs_for_the_human_and_rides_the_wire(path: str):
    """El agujero del 2026-07-19 en su forma más cara: sin guardián no hay
    overlay de usuario vulnerable, y el usuario frágil recibe el registro
    abrasivo crudo."""
    outcome = await _run(path)
    outcome.guardian.assert_awaited_once()
    assert outcome.guardian.await_args.kwargs["user_id"] == str(HUMAN_ID), (
        f"[{path}] el guardián clasificó a alguien que no es el humano que escribió"
    )
    assert "GUIA-DEL-GUARDIAN" in (_chat_kwargs(outcome)["behavioral_guidance"] or ""), (
        f"[{path}] la guía del guardián no viajó en el wire"
    )


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_other_people_rides_the_wire(path: str):
    """El agujero de 2026-06-03: la persona recuerda a Alex cuando Alex escribe
    y la niega cuando preguntan por ella. El runner reconstruye los facts del
    AUTOR; los de los terceros sólo llegan si el gateway los manda."""
    outcome = await _run(path)
    assert _chat_kwargs(outcome)["other_people"] == "OTROS: alex…", f"[{path}] el bloque de terceros no viajó"
    assert outcome.other_people.await_args.kwargs["exclude_user_id"] == str(HUMAN_ID)


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_relevant_memory_rides_the_wire(path: str):
    """Los dos modos de recuperación (keyword sobre el canal, semántico sobre
    los facts del autor) viajan en su seam dedicado, nunca dentro del hilo
    replayed."""
    outcome = await _run(path)
    relevant = _chat_kwargs(outcome)["relevant_memory"] or ""
    assert "algo viejo" in relevant, f"[{path}] la recuperación por keyword no llegó"
    assert "le importa el encuadre" in relevant, f"[{path}] la recuperación semántica de facts no llegó"
    assert outcome.client.memory.search_facts_semantic.await_args.args[0] == str(HUMAN_ID)


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_the_humans_turn_is_persisted(path: str):
    """Sin esta fila la memoria longitudinal guarda sólo la mitad de la
    conversación (encontrado el 2026-07-19: cero filas de usuario desde el
    cutover) y la transcripción de imágenes no tiene dónde aterrizar."""
    outcome = await _run(path)
    user_rows = [c for c in outcome.client.memory.store.await_args_list if c.args[3] == "user"]
    assert user_rows, f"[{path}] el turno del humano nunca se persistió"
    assert user_rows[0].args[1] == str(HUMAN_ID)
    assert user_rows[0].kwargs.get("discord_message_id") == str(TRIGGER_ID), (
        f"[{path}] la fila del humano se guardó sin su discord_message_id — "
        "el dedupe entre puertas y el append de visión dependen de él"
    )


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_reactions_land_on_the_humans_message(path: str):
    """El bug del 2026-07-14: sin mensaje disparador resuelto las `[REACT:]` del
    path de invite se morían en silencio."""
    outcome = await _run(path, reply_text="Corta.[REACT:🦅,🎞️]")
    outcome.add_reactions.assert_awaited_once()
    assert outcome.add_reactions.await_args.args[0] is outcome.message, (
        f"[{path}] las reacciones no cayeron en el mensaje del humano"
    )
    assert "REACT" not in outcome.sent, f"[{path}] el marcador se filtró a Discord"


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_durable_markers_persist_under_the_humans_id(path: str):
    """`[REMEMBER:]` (y sus hermanos durables) escriben contra el user_id que la
    puerta haya decidido pasar. Si una puerta pasa otro id, los facts del humano
    se van a la cuenta equivocada — y el marcador nunca debe llegar al canal."""
    outcome = await _run(path, reply_text="Anotado.[REMEMBER: le importa el encuadre]")
    outcome.persist_remembers.assert_awaited_once()
    assert outcome.persist_remembers.await_args.args[1] == str(HUMAN_ID), (
        f"[{path}] el fact se guardó bajo un id que no es el del humano"
    )
    assert "REMEMBER" not in outcome.sent, f"[{path}] el marcador se filtró a Discord"


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_gifs_post_as_their_own_bare_message(path: str):
    """El `[GIF:]` sale como mensaje suelto (Discord sólo hace unfurl limpio de
    una URL sola) y el marcador nunca se filtra."""
    url = "https://tenor.com/view/algo-123"
    outcome = await _run(path, reply_text="Mira.[GIF: algo]", gif_urls=(url,))
    assert any(call.args and call.args[0] == url for call in outcome.channel.send.call_args_list), (
        f"[{path}] el GIF no se posteó"
    )
    assert "GIF:" not in outcome.sent, f"[{path}] el marcador se filtró a Discord"


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_long_replies_are_chunked_and_tagged_once(path: str):
    """El cap de Discord y el tag de deploy son de la entrega compartida: una
    puerta que mandara `channel.send(texto)` a pelo reventaría en 2000 chars."""
    outcome = await _run(path, reply_text="x" * (DISCORD_LIMIT + 100))
    pieces = [call.args[0] for call in outcome.channel.send.call_args_list if call.args]
    assert len(pieces) >= 2, f"[{path}] una respuesta arriba del cap salió en un solo send"
    assert all(len(piece) <= 2000 for piece in pieces), f"[{path}] una pieza rebasó el cap duro de Discord"
    assert sum(VERSION_TAG in piece for piece in pieces) == 1, (
        f"[{path}] el tag de versión no salió exactamente una vez"
    )


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_the_typing_keepalive_covers_the_runner_call(path: str):
    """La llamada al runner puede tardar minutos; sin el keepalive el humano ve
    silencio y cree que la persona está muerta."""
    outcome = await _run(path)
    assert outcome.channel.typing.called, f"[{path}] no hubo keepalive de typing durante el turno"


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_fact_extraction_runs_in_the_background(path: str):
    """El backstop ADD-only detrás del `[REMEMBER:]` explícito: corre DESPUÉS de
    la entrega, con el id y el nombre del humano."""
    outcome = await _run(path)
    outcome.spawn_facts.assert_called_once()
    assert outcome.spawn_facts.call_args.args[0] == str(HUMAN_ID), f"[{path}] se extrajeron facts de otra persona"
    assert outcome.spawn_facts.call_args.args[2][-1]["content"] == ASK


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_images_are_transcribed_into_the_stored_row(path: str):
    """Una imagen vive dentro de UN turno y se evapora; la transcripción es el
    único rastro que queda para mañana."""
    outcome = await _run(path, attachments=[_image_attachment()])
    outcome.spawn_vision.assert_called_once()
    assert outcome.spawn_vision.call_args.args[1] == str(TRIGGER_ID), (
        f"[{path}] la transcripción apunta a otra fila que la del mensaje con la imagen"
    )


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_auto_tts_is_considered_after_delivery(path: str):
    """La voz cuelga de la entrega compartida; una puerta sin ella dejaría media
    conversación muda sin que nadie se entere."""
    outcome = await _run(path, reply_text="Un párrafo entero sobre el encuadre.", auto_tts_min_chars=1)
    outcome.speak.assert_awaited_once()
    assert outcome.speak.await_args.kwargs["reason"] == "auto"


# --- Sección C: las asimetrías REALES (rojo honesto) --------------------------


@pytest.mark.parametrize(
    "path",
    [
        MENTION,
        INVITE,
    ],
)
async def test_both_doors_stamp_that_a_message_was_seen(path: str):
    """`last_message_seen` se estampaba SÓLO en `_handle`. El detector de "vivo
    pero mudo" de /health compara seen > delivered, así que en el path primario
    —post-cutover el host es dueño de la recepción, o sea TODO entra por invite—
    no podía sonar jamás: una persona que tomaba un invite y no contestaba se veía
    idéntica a una sin tráfico. La señal anti-boot-zombie del 2026-06-13, apagada
    en el único camino donde hoy pasa algo. Arreglado el 2026-08-06.
    """
    outcome = await _run(path)
    assert outcome.client.last_message_seen is not None, (
        f"[{path}] el turno no dejó marca de 'mensaje visto' — /health no puede detectar mutismo aquí"
    )
    assert outcome.client.last_turn_delivered is not None


@pytest.mark.parametrize(
    "path",
    [
        MENTION,
        INVITE,
    ],
)
async def test_a_failed_user_store_never_costs_the_reply(path: str):
    outcome = await _run(path, guarded=True, user_store_raises=True)
    assert "encuadre corta" in outcome.sent, f"[{path}] una escritura fallida a Postgres se comió la respuesta"


@pytest.mark.parametrize(
    "path",
    [
        MENTION,
        INVITE,
    ],
)
async def test_a_broken_attachment_degrades_to_text_never_to_silence(path: str):
    outcome = await _run(path, guarded=True, ingest_raises=True, attachments=[_image_attachment()])
    assert "encuadre corta" in outcome.sent, f"[{path}] un adjunto corrupto se comió la respuesta"


@pytest.mark.parametrize(
    "path",
    [
        MENTION,
        INVITE,
    ],
)
async def test_the_corpus_is_queried_with_what_the_human_said(path: str):
    outcome = await _run(path, corpus_block="REFERENCIAS: …")
    assert outcome.corpus.await_args.kwargs["query"] == ASK, (
        f"[{path}] el corpus se recuperó con «{outcome.corpus.await_args.kwargs['query']}» "
        f"en vez de con lo que el humano preguntó"
    )


async def test_no_turn_ever_writes_facts_under_the_bots_own_id():
    """Un invite SIN sujeto humano —trigger de bot, trigger no fetchable, o el
    `[INVITE:]` de una hermana— llega con el id del PROPIO BOT como `user_id`.
    Hasta el 2026-09-09 un `[REMEMBER:]` en ese turno escribía facts en la cuenta
    de la persona-bot, y la persona los releía después como si fueran de alguien.

    Cerrado descartándolos: `bot_user_id` ya viajaba hasta `TurnRunner`, así que
    el router de marcadores puede reconocer el caso y tirar el fact con un log
    (`remember_discarded_no_human_subject`). Un fact sin dueño no se reubica —
    no hay a quién pertenecer.

    `_handle` no puede caer aquí: siempre tiene humano.
    """
    outcome = await _run(
        INVITE,
        author_is_bot=True,
        reply_text="Anotado.[REMEMBER: algo]",
    )
    ids_written = {call.args[1] for call in outcome.persist_remembers.await_args_list}
    assert str(BOT_ID) not in ids_written, "un turno sin sujeto humano escribió facts bajo el id del propio bot"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "La OTRA mitad del mismo turno sin sujeto humano, y ésta sigue abierta: al runner se "
        "le sigue mandando el id del bot como `user_id`, así que reconstruye 'los facts del "
        "autor' de un autor que no existe. La mitad de los facts durables ya se cerró "
        "(2026-09-09) porque `bot_user_id` viajaba por separado y bastaba con descartar. "
        "Ésta no se cierra igual: el runner NECESITA un id para armar el turno y elegir qué "
        "mandarle en vez del bot es una decisión de contrato, no un guard — un centinela, un "
        "id nulo que el runner sepa leer, o el propio channel_id. Se deja roja hasta que esa "
        "decisión se tome, en vez de taparla con un valor inventado."
    ),
)
async def test_the_runner_never_receives_the_bot_as_the_turns_subject():
    outcome = await _run(
        INVITE,
        author_is_bot=True,
        reply_text="Anotado.",
    )
    assert _chat_kwargs(outcome)["user_id"] != str(BOT_ID), (
        "el runner reconstruyó los facts del bot como si fuera un usuario"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "La capacidad 'una edición que AGREGA la dirección invoca a la persona' (P0 2026-07-06: "
        "Alex mandó su lista limpia y editó '@frugi' encima) existe SÓLO en el path de "
        "@mención, y `on_message_edit` se auto-suprime cuando el host es dueño de la "
        "recepción — que es la config viva. El host no tiene listener de ediciones, así que "
        "hoy, en un guild, editar para llamar a una persona no despierta a NADIE. La misma "
        "clase del 'invite path olvidado', en espejo."
    ),
)
def test_the_edit_summon_survives_the_host_cutover():
    edit_src = inspect.getsource(PersonaClient.on_message_edit)
    if "host_owns_reception" not in edit_src:
        pytest.skip("el gateway ya no se auto-suprime en ediciones")
    from demux_ai import host_client

    assert "on_message_edit" in inspect.getsource(host_client), (
        "el gateway apaga el summon-por-edición cuando el host manda, y el host no escucha ediciones"
    )


# --- Sección D: las asimetrías DELIBERADAS (no las 'arregles') ----------------


def test_stt_ownership_is_split_on_purpose():
    """El host es el ÚNICO que transcribe en un guild (`.claude/rules/voice.md`):
    rutea a partir de lo que se DIJO, y manda las palabras en `trigger_transcript`.
    El gateway transcribe sólo en DM, donde el host es estructuralmente sordo
    (Discord aísla el canal de DM por bot user). No es una capacidad olvidada:
    es un dueño único con una excepción de superficie."""
    assert "trigger_transcript" in inspect.signature(PersonaClient.respond_to_invite).parameters, (
        "el path de invite dejó de recibir la transcripción del host"
    )
    ingest_src = inspect.getsource(MessageIngest.dm_voice_transcript)
    assert 'getattr(message, "guild", None) is not None' in ingest_src, (
        "el gateway dejó de acotar su STT a los DMs — sería un segundo consumidor de susurro"
    )


async def test_a_guild_mention_never_calls_stt():
    """La resistencia del test anterior: en un guild el path de @mención no toca
    susurro ni para leer el adjunto."""
    client = _client()
    client._ingest._stt_client = MagicMock()
    channel = _channel()
    message = _human_message(channel)
    with patch("persona_gateway.ingest.transcribe_voice_message", new_callable=AsyncMock) as stt:
        assert await client._ingest.dm_voice_transcript(message) == ""
    stt.assert_not_awaited()


@pytest.mark.parametrize("predicate", ["should_respond", "edit_summons"])
def test_reception_predicates_are_mention_only_by_construction(predicate: str):
    """`should_respond`/`edit_summons` deciden si la persona se AUTO-invoca. Un
    invite ya viene decidido por el host: exigirle esos predicados sería pedirle
    permiso dos veces y volver a la 'ventana de dos bots peleando'."""
    reception = inspect.getsource(PersonaClient.on_message) + inspect.getsource(PersonaClient.on_message_edit)
    assert f"{predicate}(" in reception, f"{predicate} dejó de gobernar la auto-invocación del path de @mención"
    assert predicate not in inspect.getsource(PersonaClient.respond_to_invite), (
        f"el path de invite empezó a consultar {predicate} — el host ya decidió; sería doble permiso"
    )


async def test_an_invite_without_trigger_drops_reactions_instead_of_failing():
    """Documentado en `turns.py`: sin mensaje disparador no hay dónde reaccionar.
    La asimetría correcta es degradar con un log de advertencia — nunca romper
    el turno, y nunca dejar el marcador visible."""
    client = _client("Corta.[REACT:🦅]")
    channel = _channel()
    with (
        patch.object(client, "get_channel", return_value=channel),
        patch("persona_gateway.turns.add_reactions", new_callable=AsyncMock) as add,
    ):
        await client.respond_to_invite(
            channel_id=CHANNEL_ID,
            guild_id="G1",
            channel_name="general",
            reason=REASON,
            invited_by="host",
            trigger_message_id=None,
        )
        await asyncio.sleep(0)
    add.assert_not_awaited()
    sent = " ".join(str(call) for call in channel.send.call_args_list)
    assert "Corta." in sent
    assert "REACT" not in sent


async def test_an_attachment_only_turn_extracts_facts_only_on_the_mention_door():
    """Divergencia tolerada, anotada para que nadie la lea como bug silencioso.

    Con una imagen y CERO texto, el path de @mención dispara igual la extracción
    (con `ask=""`, sobre la ventana reciente) y el de invite la salta
    (`subject_ask` vacío). El costo de la divergencia es una llamada al juez de
    más en una puerta, no un dato perdido: lo que la imagen aportaba lo escribe
    la transcripción de visión, que SÍ corre en las dos. Si algún día se
    unifica, la puerta que sobra es la de @mención.
    """
    mention = await _run(MENTION, content="", attachments=[_image_attachment()])
    invite = await _run(INVITE, content="", attachments=[_image_attachment()])
    mention.spawn_facts.assert_called_once()
    invite.spawn_facts.assert_not_called()
    mention.spawn_vision.assert_called_once()
    invite.spawn_vision.assert_called_once()


@pytest.mark.parametrize("path", BOTH_PATHS)
async def test_neither_door_stamps_delivery_when_nothing_was_sent(path: str):
    """El estado "vio un mensaje y no contestó" tiene que ser ALCANZABLE.

    `tests/core/test_gateway_liveness.py::test_message_seen_but_no_reply_past_grace_is_mute`
    lleva desde el 2026-06-13 describiendo este escenario en verde, pero arma el
    estado a mano: en producción, con el sello incondicional, `delivered` siempre
    quedaba después de `seen` y `mute_suspected` no podía encenderse por esta vía.

    Es el turno del 2026-08-11 22:08 UTC — el runner se reinició a media petición
    y devolvió texto vacío. Con el sello puesto, /health lo reportaba entregado.
    Issue #40, confirmado por KQL el 2026-08-19.
    """
    outcome = await _run(path, reply_text="")

    assert outcome.client.last_message_seen is not None, f"[{path}] el turno ni siquiera dejó marca de 'mensaje visto'"
    assert outcome.client.last_turn_delivered is None, (
        f"[{path}] se selló la entrega de un turno que no mandó NADA — /health vuelve a mentir"
    )
