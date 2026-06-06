"""Khimeras persona registry — the "factory".

Each sibling bot (Vultur, and future ones) is ONE entry here + one `<id>.md`
in this directory + one Discord bot token. They all share the same brain (the
insult-runner) via `persona_id`; the entry only describes identity and how the
gateway reaches Discord for that face.

Adding a bot:
  1. Write `shared/personas/<id>.md` (its DNA / system prompt).
  2. Create a Discord app → bot token → invite to Khimeras (View/Send/History).
  3. Add an entry below with `token_env` pointing at that token's env var.
  4. Store the token as a Container App secret + in ~/.secrets/.

The plumbing/gateway (PR3) reads this to know which gateways to start and which
`persona_id` to send the runner per @mention. `persona_id` == the dict key and
MUST match `^[a-z0-9_]{1,32}$` (the runner's allowlist) and the `<id>.md` stem.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    persona_id: str  # runner persona_id + filename stem; [a-z0-9_]{1,32}
    display_name: str  # shown in Discord (the bot user's name)
    persona_file: str  # filename under shared/personas/ shipped to the runner
    token_env: str  # env var holding this bot user's Discord token
    avatar: str | None = None  # optional avatar image path/URL set at app creation


# MVP: Vultur only. Insult is NOT here — it is not a sibling persona, it is the
# omnipresent host with its own plumbing and its own default persona.md.
PERSONAS: dict[str, Persona] = {
    "vultur": Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
        avatar=None,
    ),
}


def get_persona(persona_id: str) -> Persona | None:
    """Return the Persona for an id, or None if unregistered."""
    return PERSONAS.get(persona_id)


def all_personas() -> list[Persona]:
    """All registered sibling personas (for the gateway to spin up)."""
    return list(PERSONAS.values())
