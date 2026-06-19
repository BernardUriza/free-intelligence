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

    # LLM model selection. There's no direct-Anthropic client anymore — all
    # generation goes through the agent runner (OAuth Max). This is just the
    # model id the runner is asked to use as the DEPTH tier when the router
    # is enabled (and the default everywhere else).
    llm_model: str = "claude-sonnet-4-6"
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

    # Boot: hard ceiling for the data-plane connect on on_ready. The healthy
    # critical path (pool + schema + pgvector, prewarm now off-path) is ~2s, so
    # this is deliberately generous — if connect() exceeds it, the replica is
    # wedged and must fail fast (exit non-zero → fresh replica) rather than
    # linger as a zombie that /debug/health reports "ok". See the 2026-06-13
    # boot-hang incident.
    boot_connect_timeout_s: float = 45.0

    # Memory
    memory_recent_limit: int = 50
    memory_relevant_limit: int = 5

    # Azure OpenAI (TTS + Whisper)
    azure_openai_endpoint: str = ""
    azure_openai_key: SecretStr = SecretStr("")
    azure_openai_tts_deployment: str = "tts"
    azure_openai_whisper_deployment: str = "whisper"
    tts_voice: str = "onyx"  # alloy, echo, fable, onyx, nova, shimmer
    # Auto-speak Insult's OWN replies at/above this length so a wall of text
    # ships a voice clip you can listen to instead of reading. 0 = off (manual 🔊
    # only). Azure-only — auto-fire is suppressed when arbor_tts_url is set
    # (voice.md: Arbor stays on-demand, automatic traffic flags the account).
    auto_tts_min_chars: int = 0
    # Optional external Arbor voice service. When ARBOR_TTS_URL is set, the
    # 🔊 reaction TTS path calls this service instead of Azure OpenAI speech.
    arbor_tts_url: str = ""
    arbor_tts_token: SecretStr = SecretStr("")
    arbor_tts_voice: str = "arbor"
    arbor_tts_timeout_seconds: float = 240.0
    # The VoiceCog (🔊 reaction) reads ANY message, including ALICE's. Insult
    # is male (onyx); ALICE is female. When the 🔊'd message was authored by
    # the ALICE bot, speak it with a female tts-1 voice instead. Identified by
    # ALICE's Discord user id (snowflake from prod logs). Empty = feature off.
    alice_bot_user_id: str = "1503983124982534284"
    alice_tts_voice: str = "nova"  # female tts-1 voice for ALICE's messages
    # Sibling-coexistence (v4.7.0): when a message DIRECTLY addresses ALICE
    # (her @mention, her managed-role mention, "@alice" text, or one of these
    # aliases), Insult stays silent so the two bots don't both answer. Mirror
    # of ALICE's own direct-address triggers (alice/cogs/chat.py) so suppression
    # and ALICE-responds fire on the SAME signals — no dead air. Intrusive
    # clinical keywords are deliberately NOT here: those are shared context both
    # may weigh in on; this gate is only for "I'm talking to ALICE, not you".
    alice_aliases: list[str] = ["amix", "ali", "alicia"]

    # Canary ingress probe (proves live Discord ingress/egress + routing — the
    # contract /debug/health couldn't prove). A dedicated canary bot posts
    # "CANARY insult <uuid>" in #canary; Insult echoes "CANARY_OK <uuid>" with no
    # LLM. All three are Discord snowflake IDs (never names). Empty = feature off.
    canary_channel_id: str = ""
    canary_bot_user_id: str = ""
    insult_bot_user_id: str = ""

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
    # All four lanes default ON now (revived 2026-05-25 after the LLMClient→
    # /v1/judge migration restored their LLM path). The real fail-closed gate
    # is INFRASTRUCTURE, not policy: an empty `moltbook_api_key` makes the
    # source None → every lane short-circuits, and inbound/outbound also need
    # `moltbook_submolts`. So a deployment without the key/submolts/runner
    # stays silent regardless of these flags; set them to False only to mute a
    # lane that IS otherwise wired. The SAFETY gates (PII redaction,
    # vulnerability/disclosure, salience) run inside each lane and are NOT
    # affected by these switches.
    moltbook_api_key: SecretStr = SecretStr("")
    moltbook_base_url: str = "https://www.moltbook.com/api/v1"
    # Comma-separated submolt names, e.g. "m/philosophy,m/ai-agents". Parsed
    # via the moltbook_submolts property to keep .env friendly (Pydantic
    # parsing of list[str] from env requires JSON, which is awkward to type).
    moltbook_submolts_raw: str = ""
    moltbook_outbound_enabled: bool = True
    moltbook_inbound_enabled: bool = True
    moltbook_engagement_enabled: bool = True
    # Heartbeat replies-to-commenters task. Polls /api/v1/home every 20
    # minutes for activity_on_your_posts and replies via the agent's own
    # LLM. See Phase 7 plan + .claude/plans/elegant-foraging-knuth.md.
    moltbook_heartbeat_enabled: bool = True
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

    # Agent SDK runner (Container App insult-runner). Every chat turn routes
    # through `AgentRunnerClient` (/v1/turn) and every one-shot utility call
    # through `RunnerJudgeClient` (/v1/judge) — both on OAuth Max. These two
    # creds are the bot's ONLY LLM backend.
    insult_agent_runner_url: str = ""
    insult_agent_runner_token: SecretStr = SecretStr("")

    # When the agent runner times out / 5xx's / rate-limits, invite ALICE to
    # take the turn instead of failing the user-facing message. ALICE reads
    # the recent channel from Postgres and replies in her own persona. The
    # user sees a continuation in voice B instead of a canned error.
    alice_failover_enabled: bool = True

    # PR-4b slice 3 — INERT switch for the gpt-4.1 host degrader. False (default)
    # keeps the honest-degradation tail on the static in-character notice and
    # NEVER builds/calls the host router → zero gpt-4.1 spend, zero prod change.
    # Flipping it True wires demux_ai.host_degrader (live gpt-4.1) into the tail
    # of a fully-failed turn only — never the happy path. That flip is a separate
    # gated act (real spend), not part of shipping the wiring.
    host_router_enabled: bool = False

    # HOST 5/6 slice A — the DETERMINISTIC shadow router. Defaults True (unlike the
    # gpt-4.1 flags above, which default False to avoid spend): the shadow is pure
    # config-only routing (no LLM, no Azure, zero cost) and behavior-NEUTRAL — it
    # only LOGS what the host would route to (``shadow_router_decision``) next to
    # where the turn actually goes. Defaulting it on is the point: a shadow gated
    # off measures nothing. Flip False as a kill switch if the per-turn log proves
    # noisy; cutover (acting on the shadow target) is a separate, later slice.
    shadow_router_enabled: bool = True

    # HOST 5/6 slice A.2 — the gpt-4.1 LLM shadow router. Defaults False (like the
    # other gpt-4.1 flags): unlike the deterministic shadow above, this one calls
    # Azure per turn and SPENDS. When True the cog builds demux_ai.llm_shadow_router
    # (gpt-4.1) and the bind-identity stage runs it OFF the critical path (a
    # background task) to LOG ``llm_shadow_router_decision`` (current vs the host
    # brain's independent target) — never acted on, no cutover. Flipping it True in
    # prod is the spend authorization itself, a deliberate gated act; the
    # deterministic shadow keeps measuring agreement for free regardless.
    llm_shadow_router_enabled: bool = False

    # HOST 5/6 slice A.2 — transport for the LLM shadow router when enabled.
    # "agentic" (default) = demux_ai.host_llm via fi_runner.CodexBackend (the
    # codex CLI; carries a ~9.5k-token agent harness per call). "direct" =
    # demux_ai.llm_shadow_router.DirectAzureLLMRouter (a plain Azure chat
    # completion — only instruction+input, hundreds of tokens). Set "direct" to
    # measure/keep the cheap path; same routing decision either way.
    llm_shadow_transport: str = "agentic"

    # HOST 5/6 slice B — the CUTOVER switch. Defaults False (behavior-neutral):
    # the demux host stops merely SHADOWING and the deterministic router's decision
    # ACTUALLY routes the turn (sets persona_id). The cut is deliberately the
    # DETERMINISTIC shadow ONLY — it's a pure function (zero added latency, no LLM,
    # no Azure spend) AND it mirrors the live @vultur rule by construction, so even
    # flipped ON the routing is byte-identical to today: a true structural no-op
    # that proves the routing seam (the textbook strangler-fig first cut). The
    # gpt-4.1 LLM router stays SHADOW-only (it's a multi-second blocking call — a
    # later sub-slice gates it to ambiguous turns with a timeout fallback). The
    # cutover handle is wired only when this is True AND shadow_router_enabled is
    # True; a cutover fault always falls back to the live rule (kill switch + fail
    # safe). Flipping it True in prod is a separate gated act — never part of
    # shipping the wiring.
    host_router_cutover_enabled: bool = False

    # ``extra="ignore"`` is the deliberate, container-appropriate posture: a
    # Container App's environment always carries vars this model doesn't model
    # (deploy metadata, plus retired settings — ANTHROPIC_API_KEY, LLM_MAX_TOKENS,
    # LLM_TIMEOUT, LLM_MAX_RETRIES — that outlived the direct-Anthropic client in
    # prod env + local .env). ``forbid`` would crash startup on any of those.
    # Trade-off accepted: a typo'd known field is silently dropped rather than
    # caught — acceptable since the fields that matter have explicit defaults and
    # are exercised by the test suite.
    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "extra": "ignore"}

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
