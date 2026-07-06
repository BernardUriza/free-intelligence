"""
fi_runner.models.config

Config loader for provider-agnostic model registries.

This module builds a ModelRegistry from a plain mapping shaped like YAML/TOML:

    backends:
      aimlapi:
        type: aimlapi
        api_key_env: AIMLAPI_KEY
        base_url_env: AIMLAPI_BASE_URL
        default_model_env: AIMLAPI_DEFAULT_MODEL

    routes:
      evidence_agent:
        backend: aimlapi
        required_features: [chat, json]

No YAML parser is required here. Applications can parse YAML/TOML/JSON however
they want and pass the resulting dict into this layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import ModelFeature
from .factory import (
    ModelBackendConfig,
    ModelBackendConfigError,
    build_model_backend,
)
from .registry import ModelRegistry, ModelRoute


class ModelRegistryConfigError(ValueError):
    """Raised when a model registry config mapping is invalid."""


@dataclass(frozen=True, slots=True)
class ModelRegistryConfig:
    """
    Declarative model registry config.

    backends:
        Backend constructor configs.

    routes:
        Agent-to-backend routes.

    default_route_key:
        Route key used as fallback, usually "*".
    """

    backends: tuple[ModelBackendConfig, ...]
    routes: tuple[ModelRoute, ...]
    default_route_key: str = "*"

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_route_key", self.default_route_key.strip())

        if not self.default_route_key:
            raise ModelRegistryConfigError("default_route_key must not be empty")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModelRegistryConfig":
        """
        Build a registry config from a YAML-like mapping.

        Accepted shapes:

            backends:
              aimlapi:
                type: aimlapi
                api_key_env: AIMLAPI_KEY

        or:

            backends:
              - name: aimlapi
                type: aimlapi

        routes may also be mapping or list shaped.
        """

        if not isinstance(data, Mapping):
            raise ModelRegistryConfigError("Model registry config must be a mapping")

        backends = _parse_backend_configs(data.get("backends", {}))
        routes = _parse_routes(data.get("routes", {}))

        default_route_key = str(data.get("default_route_key", "*"))

        return cls(
            backends=tuple(backends),
            routes=tuple(routes),
            default_route_key=default_route_key,
        )


def build_model_registry(
    config: ModelRegistryConfig,
    *,
    env: Mapping[str, str] | None = None,
    clients: Mapping[str, Any] | None = None,
) -> ModelRegistry:
    """
    Build a ModelRegistry from declarative config.

    Args:
        config:
            Parsed ModelRegistryConfig.
        env:
            Optional env mapping for resolving *_env references.
        clients:
            Optional test clients keyed by backend name. This allows smoke tests
            without network calls or credits.

    Returns:
        Configured ModelRegistry.
    """

    registry = ModelRegistry(default_route_key=config.default_route_key)
    injected_clients = clients or {}

    for backend_config in config.backends:
        backend = build_model_backend(
            backend_config,
            env=env,
            client=injected_clients.get(backend_config.name),
        )
        registry.register_backend(backend)

    for route in config.routes:
        registry.register_route(route)

    return registry


def build_model_registry_from_mapping(
    data: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    clients: Mapping[str, Any] | None = None,
) -> ModelRegistry:
    """
    Convenience wrapper: mapping -> ModelRegistryConfig -> ModelRegistry.
    """

    return build_model_registry(
        ModelRegistryConfig.from_mapping(data),
        env=env,
        clients=clients,
    )


def _parse_backend_configs(raw_backends: Any) -> list[ModelBackendConfig]:
    if raw_backends is None:
        raw_backends = {}

    configs: list[ModelBackendConfig] = []

    if isinstance(raw_backends, Mapping):
        for name, raw_config in raw_backends.items():
            if not isinstance(raw_config, Mapping):
                raise ModelRegistryConfigError(
                    f"Backend config for {name!r} must be a mapping"
                )

            config_data = dict(raw_config)
            config_data.setdefault("name", str(name))

            try:
                configs.append(ModelBackendConfig.from_mapping(config_data))
            except ModelBackendConfigError as exc:
                raise ModelRegistryConfigError(
                    f"Invalid backend config for {name!r}: {exc}"
                ) from exc

        return configs

    if isinstance(raw_backends, list):
        for index, raw_config in enumerate(raw_backends):
            if not isinstance(raw_config, Mapping):
                raise ModelRegistryConfigError(
                    f"Backend config at index {index} must be a mapping"
                )

            try:
                configs.append(ModelBackendConfig.from_mapping(raw_config))
            except ModelBackendConfigError as exc:
                raise ModelRegistryConfigError(
                    f"Invalid backend config at index {index}: {exc}"
                ) from exc

        return configs

    raise ModelRegistryConfigError(
        "Config field 'backends' must be either a mapping or list"
    )


def _parse_routes(raw_routes: Any) -> list[ModelRoute]:
    if raw_routes is None:
        raw_routes = {}

    routes: list[ModelRoute] = []

    if isinstance(raw_routes, Mapping):
        for agent_id, raw_route in raw_routes.items():
            route = _parse_route(agent_id=str(agent_id), raw_route=raw_route)
            routes.append(route)

        return routes

    if isinstance(raw_routes, list):
        for index, raw_route in enumerate(raw_routes):
            if not isinstance(raw_route, Mapping):
                raise ModelRegistryConfigError(
                    f"Route config at index {index} must be a mapping"
                )

            agent_id = raw_route.get("agent_id")
            if agent_id is None:
                raise ModelRegistryConfigError(
                    f"Route config at index {index} must include 'agent_id'"
                )

            routes.append(_parse_route(agent_id=str(agent_id), raw_route=raw_route))

        return routes

    raise ModelRegistryConfigError(
        "Config field 'routes' must be either a mapping or list"
    )


def _parse_route(*, agent_id: str, raw_route: Any) -> ModelRoute:
    """
    Parse one route.

    Accepted compact form:

        routes:
          evidence_agent: aimlapi

    Full form:

        routes:
          evidence_agent:
            backend: aimlapi
            model: some-model
            required_features: [chat, json]
    """

    if isinstance(raw_route, str):
        return ModelRoute(
            agent_id=agent_id,
            backend=raw_route,
        )

    if not isinstance(raw_route, Mapping):
        raise ModelRegistryConfigError(
            f"Route config for {agent_id!r} must be a mapping or backend string"
        )

    route_data = dict(raw_route)

    backend = route_data.get("backend")
    if backend is None:
        raise ModelRegistryConfigError(
            f"Route config for {agent_id!r} must include 'backend'"
        )

    model = route_data.get("model")

    required_features_raw = route_data.get(
        "required_features",
        route_data.get("features", []),
    )
    if required_features_raw is None:
        required_features_raw = []

    required_features = _parse_features(
        required_features_raw,
        field_name=f"routes.{agent_id}.required_features",
    )

    metadata_raw = route_data.get("metadata", {})
    if metadata_raw is None:
        metadata_raw = {}

    if not isinstance(metadata_raw, Mapping):
        raise ModelRegistryConfigError(
            f"Route metadata for {agent_id!r} must be a mapping"
        )

    return ModelRoute(
        agent_id=agent_id,
        backend=str(backend),
        model=str(model).strip() if model is not None else None,
        required_features=frozenset(required_features),
        metadata=dict(metadata_raw),
    )


def _parse_features(raw_features: Any, *, field_name: str) -> frozenset[ModelFeature]:
    if isinstance(raw_features, str):
        raw_features = [raw_features]

    if not isinstance(raw_features, (list, tuple, set, frozenset)):
        raise ModelRegistryConfigError(f"{field_name} must be a list of feature names")

    features: list[ModelFeature] = []

    allowed = {
        "chat",
        "json",
        "streaming",
        "tools",
        "vision",
        "embeddings",
        "reasoning",
    }

    for raw_feature in raw_features:
        feature = str(raw_feature).strip()
        if feature not in allowed:
            raise ModelRegistryConfigError(
                f"Unknown model feature {feature!r} in {field_name}"
            )
        features.append(feature)  # type: ignore[arg-type]

    return frozenset(features)
