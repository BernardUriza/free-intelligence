"""
fi_runner.models.factory

Factory helpers for constructing model backends from explicit config.

This module does not read ~/.secrets and does not hardcode provider secrets.
It may resolve values from an injected environment mapping, defaulting to
os.environ for application-level wiring.

No network calls are performed here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .contracts import ModelBackend, ModelFeature
from .openai_compatible import OpenAICompatibleBackend
from .providers import AimlAPIBackend, FeatherlessBackend


BackendType = Literal["openai_compatible", "aimlapi", "featherless"]


class ModelBackendConfigError(ValueError):
    """Raised when a model backend config is invalid or incomplete."""


@dataclass(frozen=True, slots=True)
class ModelBackendConfig:
    """
    Declarative backend config.

    Explicit values win over env references.

    Example:
        ModelBackendConfig(
            backend_type="aimlapi",
            name="aimlapi",
            api_key_env="AIMLAPI_KEY",
            base_url_env="AIMLAPI_BASE_URL",
            default_model_env="AIMLAPI_DEFAULT_MODEL",
        )
    """

    backend_type: BackendType
    name: str

    provider: str | None = None

    api_key: str | None = None
    api_key_env: str | None = None

    base_url: str | None = None
    base_url_env: str | None = None

    default_model: str | None = None
    default_model_env: str | None = None

    features: frozenset[ModelFeature] = field(default_factory=frozenset)

    supports_json_object: bool = True
    supports_json_schema: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())

        if self.provider is not None:
            object.__setattr__(self, "provider", self.provider.strip())

        if not self.name:
            raise ModelBackendConfigError("ModelBackendConfig.name must not be empty")

        if self.provider == "":
            raise ModelBackendConfigError("ModelBackendConfig.provider must not be empty")

        if not isinstance(self.features, frozenset):
            object.__setattr__(self, "features", frozenset(self.features))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModelBackendConfig":
        """
        Build config from a mapping, accepting either "type" or "backend_type".

        This is useful for future YAML/TOML loaders without forcing config file
        parsing into the model layer.
        """

        backend_type = data.get("backend_type", data.get("type"))
        if backend_type is None:
            raise ModelBackendConfigError(
                "Backend config must include 'backend_type' or 'type'"
            )

        features = data.get("features", frozenset())
        if features is None:
            features = frozenset()

        return cls(
            backend_type=backend_type,
            name=data["name"],
            provider=data.get("provider"),
            api_key=data.get("api_key"),
            api_key_env=data.get("api_key_env"),
            base_url=data.get("base_url"),
            base_url_env=data.get("base_url_env"),
            default_model=data.get("default_model"),
            default_model_env=data.get("default_model_env"),
            features=frozenset(features),
            supports_json_object=bool(data.get("supports_json_object", True)),
            supports_json_schema=bool(data.get("supports_json_schema", False)),
            metadata=dict(data.get("metadata", {})),
        )


def build_model_backend(
    config: ModelBackendConfig,
    *,
    env: Mapping[str, str] | None = None,
    client: Any | None = None,
) -> ModelBackend:
    """
    Construct a backend from explicit config.

    Args:
        config:
            Declarative backend config.
        env:
            Optional environment mapping. Defaults to os.environ.
        client:
            Optional injected client for tests.

    Returns:
        A ModelBackend implementation.

    Raises:
        ModelBackendConfigError when required values are missing.
    """

    source_env = env if env is not None else os.environ

    api_key = _resolve_required_value(
        explicit=config.api_key,
        env_name=config.api_key_env,
        env=source_env,
        field_name="api_key",
        backend_name=config.name,
    )
    base_url = _resolve_required_value(
        explicit=config.base_url,
        env_name=config.base_url_env,
        env=source_env,
        field_name="base_url",
        backend_name=config.name,
    )
    default_model = _resolve_required_value(
        explicit=config.default_model,
        env_name=config.default_model_env,
        env=source_env,
        field_name="default_model",
        backend_name=config.name,
    )

    features = set(config.features) if config.features else None

    if config.backend_type == "aimlapi":
        return AimlAPIBackend(
            name=config.name,
            provider=config.provider or "aimlapi",
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            features=features,
            client=client,
            supports_json_object=config.supports_json_object,
            supports_json_schema=config.supports_json_schema,
        )

    if config.backend_type == "featherless":
        return FeatherlessBackend(
            name=config.name,
            provider=config.provider or "featherless",
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            features=features,
            client=client,
            supports_json_object=config.supports_json_object,
            supports_json_schema=config.supports_json_schema,
        )

    if config.backend_type == "openai_compatible":
        return OpenAICompatibleBackend(
            name=config.name,
            provider=config.provider or config.name,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            features=features,
            client=client,
            supports_json_object=config.supports_json_object,
            supports_json_schema=config.supports_json_schema,
        )

    raise ModelBackendConfigError(f"Unsupported backend_type: {config.backend_type!r}")


def _resolve_required_value(
    *,
    explicit: str | None,
    env_name: str | None,
    env: Mapping[str, str],
    field_name: str,
    backend_name: str,
) -> str:
    if explicit is not None and explicit.strip():
        return explicit.strip()

    if env_name is not None and env_name.strip():
        value = env.get(env_name.strip())
        if value is not None and value.strip():
            return value.strip()

    raise ModelBackendConfigError(
        f"Missing required {field_name!r} for model backend {backend_name!r}. "
        f"Provide it explicitly or configure {field_name}_env."
    )
