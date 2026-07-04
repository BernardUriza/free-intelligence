"""Neutral runtime/infra config for any persona-bot host.

The persona_gateway (and any future host that spins up sibling persona-bots)
needs three pieces of RUNTIME INFRA — the shared Postgres DSN and the agent
runner URL + token. These are env-backed and carry zero persona identity, so
sourcing them must NOT require importing a persona's Settings: doing that would
make the host reach into a persona, which is the exact boundary the demux is
removing.

`PersonaRuntimeConfig.from_env()` reads the env vars (POSTGRES_URL,
INSULT_AGENT_RUNNER_URL, INSULT_AGENT_RUNNER_TOKEN, plus INSULT_TO_ALICE_TOKEN for
the gateway's ported /invite endpoint) with the same dotenv-over-shell priority
that `personas.insult.config.Settings` used, so the host's behavior is unchanged —
the only thing that moves is WHERE the values are read from (a neutral shared type
instead of a persona package).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

_ENV_FILE = Path(__file__).resolve().parents[2] / "personas" / ".env"


class PersonaRuntimeConfig(BaseSettings):
    postgres_url: SecretStr = SecretStr("")
    insult_agent_runner_url: str = ""
    insult_agent_runner_token: SecretStr = SecretStr("")
    insult_to_alice_token: SecretStr = SecretStr("")

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
        """dotenv wins over shell env vars — mirrors personas.insult.config."""
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    @classmethod
    def from_env(cls) -> PersonaRuntimeConfig:
        return cls()
