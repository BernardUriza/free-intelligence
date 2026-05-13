"""ALICE settings — Pydantic Settings singleton, .env-first.

Shared infrastructure with Insult:
- Same `POSTGRES_URL` (reads the `messages` table to see the conversation
  it's about to join).
- Same `DEBUG_TOKEN` for the optional read-only introspection endpoint.

ALICE-specific:
- `ALICE_DISCORD_TOKEN` — separate Discord application from Insult's bot.
- `OPENAI_API_KEY` — GPT-4.1 access (Alex chose 4.1 for therapy work; see
  persona.md philosophy section).
- `INSULT_TO_ALICE_TOKEN` — shared secret on the `/invite` REST endpoint
  so only the Insult bot can summon ALICE through that path. Mentions from
  Discord users bypass this (they're authed by Discord itself).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AliceSettings(BaseSettings):
    """ALICE runtime configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Discord ---
    alice_discord_token: str = Field(
        default="",
        description="ALICE's Discord bot token (separate app from Insult).",
    )

    # --- OpenAI ---
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for GPT-4.1 access.",
    )
    openai_model: str = Field(
        default="gpt-4.1",
        description="Primary model. GPT-4.1 chosen explicitly for therapy work.",
    )
    openai_max_tokens: int = Field(default=2048)
    openai_timeout_seconds: float = Field(default=60.0)

    # --- Postgres (shared with Insult) ---
    postgres_url: str = Field(
        default="",
        description="Same DSN as Insult — ALICE reads/writes the shared messages table.",
    )

    # --- REST /invite endpoint ---
    invite_host: str = Field(default="0.0.0.0")  # noqa: S104 — Container App ingress requires bind-all; restrict via firewall/CIDR upstream
    invite_port: int = Field(default=8788)
    insult_to_alice_token: str = Field(
        default="",
        description="Shared secret. Only the Insult bot has this; required on the /invite endpoint.",
    )

    # --- Memory window ---
    memory_recent_limit: int = Field(
        default=30,
        description="How many recent messages ALICE pulls from the shared channel before responding.",
    )

    # --- Persona ---
    persona_path: str = Field(
        default="alice/persona.md",
        description="Path to ALICE's system-prompt persona (mtime-aware reload).",
    )


settings = AliceSettings()
