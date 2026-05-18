"""ALICE settings — Pydantic Settings singleton, .env-first.

Shared infrastructure with Insult:
- Same `POSTGRES_URL` (reads the `messages` table to see the conversation
  it's about to join).
- Same `AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_KEY` cognitive account
  (`insult-openai`) — ALICE consumes the `gpt-4.1` deployment, Insult uses
  the `tts` / `whisper` deployments. One Azure resource, one factura.
- Same `DEBUG_TOKEN` for the optional read-only introspection endpoint.

ALICE-specific:
- `ALICE_DISCORD_TOKEN` — separate Discord application from Insult's bot.
- `AZURE_OPENAI_GPT_DEPLOYMENT` — deployment name for chat completions
  (defaults to `gpt-4.1`; Alex chose 4.1 for therapy work).
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

    # --- Azure OpenAI (shared cognitive account `insult-openai`) ---
    azure_openai_endpoint: str = Field(
        default="",
        description="Azure OpenAI resource endpoint, e.g. https://northcentralus.api.cognitive.microsoft.com/",
    )
    azure_openai_key: str = Field(
        default="",
        description="API key for the Azure OpenAI cognitive account.",
    )
    azure_openai_gpt_deployment: str = Field(
        default="gpt-4.1",
        description="Deployment name in the cognitive account for chat completions.",
    )
    azure_openai_api_version: str = Field(
        default="2025-04-01-preview",
        description="Azure OpenAI REST API version; pinned so SDK upgrades don't surprise prod.",
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

    # --- Sibling coexistence ---
    # When ALICE detects one of these patterns in a non-mention message,
    # she responds anyway (intrusive mode). The list is intentionally
    # short and high-precision — false positives = ALICE talking over a
    # conversation she wasn't invited to. See plan
    # `.claude/plans/sibling_bot_coexistence.md` addendum 2026-05-18.
    intrusive_mode_enabled: bool = Field(
        default=True,
        description="Allow ALICE to respond without explicit @mention when clinical-disclosure keywords appear.",
    )
    alice_aliases: list[str] = Field(
        default=["amix", "ali", "alicia"],
        description="Lowercase aliases that count as addressing ALICE. 'alice' is implicit.",
    )
    insult_bot_user_id: str = Field(
        default="",
        description="Insult's Discord bot user ID. Used to filter cross-sibling listener so ALICE only reacts to Insult's messages, not to all bots in the channel.",
    )


settings = AliceSettings()
