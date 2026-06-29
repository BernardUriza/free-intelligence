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

from dataclasses import dataclass, field


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


# Insult is NOT here — it is the omnipresent host, not a sibling persona.
# ALICE is also NOT here — she predates the registry; Insult has her hardcoded.
# Future bots: add an entry, nothing else to change.
PERSONAS: dict[str, Persona] = {
    "vultur": Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
        bot_user_id="1512687836766404618",  # set on 2026-06-06
        aliases=[],  # no text aliases for now — @mention-only to avoid FP
        avatar=None,
    ),
}


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


def sibling_aliases() -> list[str]:
    """Flat list of all text aliases across registered siblings.

    Used for text-mention suppression (when @mention isn't used).
    Each persona controls its own alias list to avoid cross-contamination.
    """
    out: list[str] = []
    for p in PERSONAS.values():
        out.extend(p.aliases)
    return out
