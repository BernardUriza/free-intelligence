"""Configuracion centralizada via .env + Pydantic Settings.

.env file takes priority over shell environment variables via
settings_customise_sources(). This prevents a stale ANTHROPIC_API_KEY
exported in the user's shell profile from overriding the project key.
"""

import sys
from pathlib import Path

import structlog
from pydantic import SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

log = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # Discord
    discord_token: SecretStr
    command_prefix: str = "!"

    # Anthropic
    anthropic_api_key: SecretStr
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 2048
    llm_timeout: float = 30.0
    llm_max_retries: int = 5
    system_prompt: str = "You are a helpful assistant."
    persona_file: Path = _PROJECT_ROOT / "persona.md"

    # Model Router (3-tier: casual/depth/crisis). See .claude/plans/model_router.md.
    # llm_model above acts as the DEPTH tier when the router is enabled.
    model_router_enabled: bool = False
    casual_model: str = "claude-haiku-4-5-20251001"
    crisis_model: str = "claude-opus-4-7"
    opus_24h_cap: int = 20

    # Preset classifier — LLM middleware that decides preset+modifiers from
    # CONTEXT (not regex). Falls back automatically to the regex classifier
    # on timeout / API error / invalid JSON. The regex classifier still runs
    # in the same turn as a shadow for divergence telemetry. Set the flag to
    # False to disable the LLM middleware entirely (regex-only kill switch).
    preset_classifier_llm_enabled: bool = True
    preset_classifier_model: str = "claude-haiku-4-5-20251001"
    preset_classifier_timeout_ms: int = 1500

    # Memory
    memory_recent_limit: int = 50
    memory_relevant_limit: int = 5

    # Azure OpenAI (TTS + Whisper)
    azure_openai_endpoint: str = ""
    azure_openai_key: SecretStr = SecretStr("")
    azure_openai_tts_deployment: str = "tts"
    azure_openai_whisper_deployment: str = "whisper"
    tts_voice: str = "onyx"  # alloy, echo, fable, onyx, nova, shimmer

    # Channel summaries (cross-channel awareness)
    summary_model: str = "claude-haiku-4-5-20251001"
    summary_interval_minutes: int = 15

    # Debug HTTP server (read-only introspection)
    # If debug_token is empty, the server does NOT start (fail-closed).
    # Default binds to localhost only. Override via DEBUG_HOST=0.0.0.0 for
    # container networking if ingress is ever enabled.
    debug_token: SecretStr = SecretStr("")
    debug_host: str = "127.0.0.1"
    debug_port: int = 8787

    # Moltbook integration (see .claude/plans/elegant-foraging-knuth.md).
    # The carretera both-ways is fail-closed by default: an empty api_key
    # disables both lanes regardless of the *_enabled flags. The flags are
    # the second gate — they let an operator stage rollout (inbound first,
    # then outbound) once the key is provisioned, mirroring how
    # is_azure_configured() gates the backup loop in bot.py.
    moltbook_api_key: SecretStr = SecretStr("")
    moltbook_base_url: str = "https://www.moltbook.com/api/v1"
    # Comma-separated submolt names, e.g. "m/philosophy,m/ai-agents". Parsed
    # via the moltbook_submolts property to keep .env friendly (Pydantic
    # parsing of list[str] from env requires JSON, which is awkward to type).
    moltbook_submolts_raw: str = ""
    moltbook_outbound_enabled: bool = False
    moltbook_inbound_enabled: bool = False
    moltbook_engagement_enabled: bool = False
    # Heartbeat replies-to-commenters task. Polls /api/v1/home every 20
    # minutes for activity_on_your_posts and replies via the agent's own
    # LLM. See Phase 7 plan + .claude/plans/elegant-foraging-knuth.md.
    moltbook_heartbeat_enabled: bool = False
    # Discord channel id where the bot reports its Moltbook activity
    # (publishes + engagement comments). Empty string disables narration.
    moltbook_report_channel_id: str = ""
    # Comma-separated agent names the bot must NOT engage with (no
    # comments, no priority lookup, no inbound digest surfacing). Use
    # for noisy / spammy / off-topic agents the operator finds
    # exhausting. Moltbook has no server-side block API — this is the
    # local equivalent.
    moltbook_blocked_authors_raw: str = "cicadafinanceintern"

    # Paths (legacy SQLite path kept for tooling that still touches files
    # during the cut-over; the live memory store no longer reads it).
    storage_dir: Path = _PROJECT_ROOT / "storage"
    db_path: Path = _PROJECT_ROOT / "storage" / "memory.db"

    # Postgres DSN — required after the 2026-05-12 migration from
    # SQLite-in-blob to Azure Database for PostgreSQL Flexible Server.
    # Format: postgresql://user:pass@host:5432/dbname?sslmode=require
    # The container reads this from POSTGRES_URL env var (Pydantic
    # uppercases the field name automatically).
    postgres_url: SecretStr = SecretStr("")

    # Agent SDK runner (Container App insult-runner). When the user_id is in
    # `insult_agent_sdk_user_ids` (comma-separated, "*" = all), the turn
    # routes through `AgentRunnerClient` (OAuth Max + workspace-grounded)
    # instead of the legacy LLMClient (API key + inline-context). Empty list
    # disables the flag entirely. See .claude/plans/insult_agent_sdk_migration.md
    insult_agent_runner_url: str = ""
    insult_agent_runner_token: SecretStr = SecretStr("")
    insult_agent_sdk_user_ids: str = ""

    # Legacy direct-Anthropic kill switch. Set to False once the agent runner
    # is canonical and the API key is revoked. Every LLMClient.chat()/
    # utility_call() returns empty fast; each aux caller already has a
    # fallback path for empty responses. The bot Container becomes pure
    # plumbing between Discord and the runner.
    legacy_llm_enabled: bool = True

    # When the agent runner times out / 5xx's / rate-limits, invite ALICE to
    # take the turn instead of failing the user-facing message. ALICE reads
    # the recent channel from Postgres and replies in her own persona. The
    # user sees a continuation in voice B instead of a canned error.
    alice_failover_enabled: bool = True

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """dotenv wins over shell env vars — prevents stale key overrides."""
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    @property
    def moltbook_submolts(self) -> list[str]:
        """Parsed submolt list from the comma-separated env value."""
        return [s.strip() for s in self.moltbook_submolts_raw.split(",") if s.strip()]

    @property
    def moltbook_blocked_authors(self) -> frozenset[str]:
        """Parsed block-list. Lowercased so author comparisons are
        case-insensitive (Moltbook display names sometimes drift case)."""
        return frozenset(a.strip().lower() for a in self.moltbook_blocked_authors_raw.split(",") if a.strip())

    def ensure_dirs(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def load_persona(self):
        """Load persona from file, overriding system_prompt."""
        if self.persona_file.exists():
            self.system_prompt = self.persona_file.read_text(encoding="utf-8")
            log.info("persona_loaded", file=str(self.persona_file), length=len(self.system_prompt))


try:
    settings = Settings()
except Exception as e:
    log.critical("config_failed", error=str(e))
    print(f"\nConfig error: {e}")
    print("Copia .env.example a .env y llena los valores.\n")
    sys.exit(1)

settings.ensure_dirs()
settings.load_persona()
