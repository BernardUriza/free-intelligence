"""Khimeras persona registry — the "factory" and source of truth.

Each sibling bot is ONE entry here + one `<id>.md` + one Discord bot token.
They all share the same brain (persona-runner) via `persona_id`.

Insult reads this at startup (via insult/config.py) to build its sibling-
suppression map: when a message @mentions any registered sibling, Insult
stays silent and lets that sibling answer. No hardcoding per bot — just
add an entry here and the whole system adapts.

Adding a bot:
  1. Write `shared/personas/<id>.md`.
  2. Create Discord app → bot token → invite to Khimeras.
  3. Add an entry below with `bot_user_id` (from Developer Portal → General).
  4. Store token as Container App secret + in ~/.secrets/.
  5. Run the gateway — it picks up the new entry automatically.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# The sibling a bare `[INVITE:]` marker summons. It lives here because the
# registry is the source of truth for who the personas ARE — `persona_gateway`
# imports it from here, and putting it in the gateway instead would force
# `markers.py` to import `invite_server.py`, which imports `gateway.py`, which
# imports `markers.py`. One home, no cycle.
DEFAULT_INVITE_PERSONA_ID = "alice"


@dataclass(frozen=True)
class Persona:
    persona_id: str  # runner persona_id + filename stem; [a-z0-9_]{1,32}
    display_name: str  # shown in Discord (bot user's display name)
    persona_file: str  # filename under shared/personas/ shipped to the runner
    token_env: str  # env var holding this bot user's Discord token
    # Discord bot user ID (from Developer Portal → General Information → App ID).
    # Used by Insult to suppress its own response when a message @mentions this
    # sibling. Set to "" if the bot hasn't been created in Discord yet.
    bot_user_id: str = ""
    # Optional text aliases that activate suppression even without an @mention
    # (e.g. someone types "vultur" as a keyword). Keep short: false-positive risk.
    aliases: list[str] = field(default_factory=list)
    avatar: str | None = None
    # Azure TTS voice for this persona's own 🔊 audio (the gateway's VoiceClient
    # speaks the persona's messages in THIS voice — onyx=Insult, nova=ALICE are
    # taken, so siblings pick a distinct one). The persona owns its voice.
    tts_voice: str = "echo"
    # Whether `persona_gateway` actually SPINS UP this bot. Decoupled from
    # registry membership on purpose: a persona can be KNOWN to the registry
    # (so Insult suppresses it, the runner can load its DNA) WITHOUT the gateway
    # starting it in prod yet. This is the cutover gate — flip to True (+ put the
    # token in the gateway env) at the single-owner cutover, never before, so
    # there is never a minute with two live bots sharing one Discord token.
    gateway_enabled: bool = True
    # Synthetic pgvector namespace of this persona's shared topic corpus in
    # deep_memory_chunks (RAG). None = no corpus. Sources live under
    # data/corpus/<persona_id>/ (gitignored; MANIFEST.md documents them) and are
    # ingested via scripts/ingest_corpus.py; the per-turn references block is
    # injected through guidance_for_turn with the header content at
    # shared/corpus/headers/<persona_id>.md.
    corpus_namespace: str | None = None


# Future bots: add an entry, nothing else to change.
PERSONAS: dict[str, Persona] = {
    # Insult — registrado 2026-07-14, el día del castigo. Dejó de ser "el
    # sistema" (personas/insult murió, 37k líneas) y volvió a ser lo que sus
    # hermanos siempre fueron: UNA persona = DNA en insult.md + esta entrada.
    # Mention-gated vía gateway por ahora; su omnipresencia regresa cuando el
    # host nuevo (demux_ai) sea dueño de la recepción. CUTOVER: el token entra
    # al env del gateway SOLO después del scale-to-0 del Container App
    # discord-bot viejo — nunca dos bots vivos con un token.
    "insult": Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="INSULT_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1488415576551325906",  # GET /users/@me con su token, 2026-07-14
        aliases=[],  # mention-only: "insult" como palabra suelta es FP-trampa (es/en)
        avatar=None,
        tts_voice="onyx",
        gateway_enabled=True,
        corpus_namespace="__corpus_insult__",  # retórica erística (Schopenhauer, maximistas)
    ),
    "vultur": Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1512687836766404618",  # set on 2026-06-06
        aliases=[],  # no text aliases for now — @mention-only to avoid FP
        avatar=None,
        # Legacy namespace name (predates per-persona convention): 2,390 chunks
        # of Braudy & Cohen 2009 + The Language and Style of Film Criticism,
        # ingested 2026-06-02/03. Keep the name — the data is already in PG.
        corpus_namespace="__corpus_film__",
    ),
    # ALICE migration (PR-4c) — readiness, NOT cutover. She is registered so the
    # runner can load her DNA (persona_id="alice") and Insult suppresses her via
    # the registry, but `gateway_enabled=False` keeps `persona_gateway` from
    # starting her: alice-bot (her legacy gpt-4.1 Container App) still owns the
    # ALICE_DISCORD_TOKEN and serves her in prod. Cutover (gated on a live
    # host-router failover replacement) flips gateway_enabled=True + moves the
    # token off alice-bot. See .claude/plans/adr_alice_to_claude_sibling.md.
    "alice": Persona(
        persona_id="alice",
        display_name="A.L.I.C.E.",
        persona_file="alice.md",
        token_env="ALICE_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1503983124982534284",
        aliases=["alice", "amix", "ali", "alicia"],
        avatar=None,
        tts_voice="nova",
        # CUTOVER (2026-06-29): flipped True. The gateway only spins ALICE up when
        # gateway_enabled AND ALICE_DISCORD_TOKEN is in its env — the token is moved
        # off alice-bot (scaled to 0 first) as the final atom, so there is never a
        # minute with two live ALICE bots on one token.
        gateway_enabled=True,
        corpus_namespace="__corpus_alice__",  # consuelo práctico (estoicos)
    ),
    # Frugívoro — erudite vegan-gastronomy sibling (2026-06-29). Born native to the
    # gateway (no legacy bot to retire, unlike ALICE), Claude persona on the
    # persona-runner. DNA in shared/personas/frugivoro.md; ships to the runner via
    # COPY shared/personas/. RAG corpus (__corpus_vegan__) is a later hardening step.
    "frugivoro": Persona(
        persona_id="frugivoro",
        display_name="Frugívoro",
        persona_file="frugivoro.md",
        token_env="FRUGIVORO_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1521273256236023989",  # Discord app/bot id, created 2026-06-29
        # "fruggy" es el apodo real de cariño en #general (issue #36): sin él, un
        # "fruggy, ¿esto lleva huevo?" no le llegaba a nadie y se perdía.
        aliases=["frugivoro", "frugi", "frugívoro", "fruggy"],
        avatar=None,
        tts_voice="fable",
        gateway_enabled=True,
        corpus_namespace="__corpus_vegan__",  # el "later hardening step" por fin (2026-07-16)
    ),
    # Unborn Being — counter-apologetics + antinatalist-mentor sibling (2026-07-16).
    # Born native to the gateway, Claude persona on the persona-runner. DNA is three
    # verbatim blocks (atheist analyst / collaborative core / antinatalist mentor) in
    # shared/personas/unborn_being.md. Benchmarked locally 11/11 before wiring.
    "unborn_being": Persona(
        persona_id="unborn_being",
        display_name="Unborn Being",
        persona_file="unborn_being.md",
        token_env="UNBORN_BEING_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1527357397884993677",  # Discord app/bot id, created 2026-07-16
        aliases=[],  # mention-only: "unborn" suelto es FP-riesgo, mismo criterio que Insult
        avatar=None,
        tts_voice="alloy",
        gateway_enabled=True,
        corpus_namespace="__corpus_unborn__",  # NDE/DMT + contra-apologética clásica
    ),
    # Valentis — quien se queda (2026-08-25). Nace de una
    # propuesta de Aníbal, que sobre su propia app dijo que sacar una beta pública
    # era peligroso "porque si hay algún sesgo, la persona no va a saber cómo
    # manejarlo, no voy a poder estar en primera mano para corregir esos errores".
    # Aquí eso no es una frase: es esta entrada. Vive SOLO en Khimeras — donde quien
    # la usa tiene nombre y hay humanos que pueden ver lo que pasó y corregirlo — y
    # arranca aliases=[] para que nadie se la tope sin querer.
    #
    # ADN y guidance los escribió Alex (issues #41 y #42): acompaña, no trata; no
    # diagnostica, no opina de medicación, no interpreta; y derivar NUNCA cierra la
    # conversación. Su preset RESPECTFUL_SERIOUS invierte a propósito el orden de
    # Insult: con deseo suicida expresado y sustancias de por medio, DERIVA antes de
    # contener, porque no puede ofrecer cuerpo y todos los manuales suponen que sí.
    #
    # El ruteo por tema NO se le abre: la revelación personal y el peso emocional
    # siguen siendo de insult, el host (ver demux_ai/prompts/host_routing.md, y los
    # dos incidentes que pusieron esa regla ahí). A Valentis se la invoca por su
    # nombre, igual que a ALICE.
    "valentis": Persona(
        persona_id="valentis",
        display_name="Valentis",
        persona_file="valentis.md",
        token_env="VALENTIS_DISCORD_TOKEN",  # nosec B106 — env-var NAME, not a secret
        bot_user_id="1541815100023767131",  # Discord app/bot id, created 2026-08-25
        aliases=[],  # mention-only: una palabra suelta que la despierte en una
        # conversación que no era para ella es peor, EN ESTE TEMA, que no estar.
        avatar=None,
        tts_voice="shimmer",  # la única libre; onyx/nova/fable/alloy/echo ocupadas
        gateway_enabled=True,
        # Fase 2 abierta el 2026-09-16 (issue #61, decisión 3 de Álex): entra con
        # ética del cuidado. Su header manda NO citar en un turno de acompañamiento.
        corpus_namespace="__corpus_valentis__",
    ),
}


def gateway_personas() -> list[Persona]:
    """Personas the gateway should actually start (gateway_enabled is True).

    Distinct from `all_personas()` (which the suppression map needs in full): a
    registered-but-not-yet-enabled persona is known to the system but not spun
    up. This is the cutover gate, in code, not an ad-hoc env flag.
    """
    return [p for p in PERSONAS.values() if p.gateway_enabled]


def get_persona(persona_id: str) -> Persona | None:
    """Return the Persona for an id, or None if unregistered."""
    return PERSONAS.get(persona_id)


def all_personas() -> list[Persona]:
    """All registered sibling personas (for the gateway to spin up)."""
    return list(PERSONAS.values())


def sibling_bot_user_ids() -> set[str]:
    """Discord user IDs of all registered sibling bots (non-empty only).

    Used by Insult's mention-suppression logic: if a message @mentions any of
    these IDs, Insult stays silent and lets that sibling answer instead.
    """
    return {p.bot_user_id for p in PERSONAS.values() if p.bot_user_id}


def persona_id_by_bot_user_id() -> dict[str, str]:
    """Map Discord bot user IDs to their registered persona_id."""
    return {p.bot_user_id: p.persona_id for p in PERSONAS.values() if p.bot_user_id}


def _normalize_role_name(value: str) -> str:
    """Return a lowercase, accent-insensitive role/persona lookup key."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.strip().lower()


def persona_id_by_role_name(role_name: str) -> str | None:
    """Resolve a Discord role name to a registered persona_id, if any.

    Matching is case/accent-insensitive and intentionally based on registry data
    rather than Discord role ids, so recreated roles keep working.

    The FULL display name is a candidate, not just its first word: a role is
    normally named exactly like the persona, so "Unborn Being" and "Vultur
    Analytica" — the two personas whose names are compound — resolved to None
    and their role mention summoned nobody. The host then fell through to
    routing by content and whoever the router liked answered instead
    (2026-07-27: a question addressed to @Unborn Being was answered by Insult).
    The first word stays a candidate too, for the shortened role ("Vultur").
    """
    role_key = _normalize_role_name(role_name)
    if not role_key:
        return None
    for persona in PERSONAS.values():
        display_first_word = persona.display_name.split(maxsplit=1)[0] if persona.display_name else ""
        candidates = [
            persona.persona_id,
            persona.display_name,
            display_first_word,
            *persona.aliases,
        ]
        if role_key in {_normalize_role_name(candidate) for candidate in candidates}:
            return persona.persona_id
    return None


def sibling_aliases() -> list[str]:
    """Flat list of all text aliases across registered siblings.

    Used for text-mention suppression (when @mention isn't used).
    Each persona controls its own alias list to avoid cross-contamination.
    """
    out: list[str] = []
    for p in PERSONAS.values():
        out.extend(p.aliases)
    return out
