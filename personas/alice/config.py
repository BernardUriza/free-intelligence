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
    invite_host: str = Field(default="0.0.0.0")  # noqa: S104  # nosec B104 — Container App ingress requires bind-all; restrict via firewall/CIDR upstream
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
    # Failover escape hatch (alice 0.1.19, 2026-05-23): when Insult is down
    # for any reason (billing exhausted, Anthropic outage, deploy churn,
    # rate-limit storm) and ALICE has to cover the channel solo. With this
    # ON, ALICE drops the mention/alias/intrusive gate in guild channels and
    # responds to EVERY non-bot message (same shape as a DM). Default off so
    # the normal sibling-coexistence behavior is unchanged; flip via
    # ALICE_OPEN_GATE_ENABLED=true on the Container App when needed, then
    # back to false once Insult is healthy. Keep this short-lived — running
    # both bots wide-open at once is the "duplicate replies" footgun the
    # passive design exists to prevent.
    open_gate_enabled: bool = Field(
        default=False,
        description="DEPRECATED manual override (alice 0.1.19). Kept for backward compat: when open_gate_mode='off' AND this is True, treated as mode='on'. Prefer ALICE_OPEN_GATE_MODE.",
    )
    # Self-governing failover (alice 0.1.21, 2026-05-24): instead of a human
    # flipping open_gate on/off around Insult's billing, ALICE decides per turn
    # by watching the shared Postgres `messages` table. Three modes:
    #   - "off":  never open-gate (normal sibling coexistence).
    #   - "on":   always open-gate (the old manual override).
    #   - "auto": open-gate ONLY when Insult has produced no assistant message
    #             in this channel for `open_gate_silence_threshold_s` seconds —
    #             i.e. he's down. The moment Insult answers again (billing
    #             recharged, outage over), his row appears and ALICE backs off
    #             on the very next turn. No restart, no cron, no babysitting.
    open_gate_mode: str = Field(
        default="off",
        description="Open-gate failover mode: off | on | auto. 'auto' = ALICE covers only while Insult is silent past the threshold, and steps back when he recovers.",
    )
    open_gate_silence_threshold_s: float = Field(
        default=300.0,
        description="In 'auto' mode, how many seconds Insult must be silent (no assistant message in-channel) before ALICE treats him as down and opens the gate.",
    )
    alice_aliases: list[str] = Field(
        default=["amix", "ali", "alicia"],
        description="Lowercase aliases that count as addressing ALICE. 'alice' is implicit.",
    )
    insult_bot_user_id: str = Field(
        default="",
        description="Insult's Discord bot user ID. Used to filter cross-sibling listener so ALICE only reacts to Insult's messages, not to all bots in the channel.",
    )
    clinical_channel_id: str = Field(
        default="",
        description="Discord channel ID (clinician-only) where ALICE posts her Clinical "
        "Reflection Layer output. Empty disables the clinical layer. This output is "
        "metacognitive and MUST stay clinician-only — it is never sent to the patient.",
    )


settings = AliceSettings()
