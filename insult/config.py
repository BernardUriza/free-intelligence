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

    # Paths
    storage_dir: Path = _PROJECT_ROOT / "storage"
    db_path: Path = _PROJECT_ROOT / "storage" / "memory.db"

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
