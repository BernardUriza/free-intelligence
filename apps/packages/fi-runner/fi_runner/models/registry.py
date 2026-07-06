"""
fi_runner.models.registry

Backend registry and routing layer for model providers.

Design goal:
    Agents ask for model work by agent_id/purpose.
    fi-runner resolves the configured backend and model.
    Domain contracts remain independent from provider details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .contracts import ModelBackend, ModelFeature


class ModelRoutingError(RuntimeError):
    """Base error for model backend routing failures."""


class ModelRouteNotConfigured(ModelRoutingError):
    """Raised when no route exists for an agent and no default route is configured."""


class ModelBackendNotRegistered(ModelRoutingError):
    """Raised when a route references a backend that is not registered."""


class ModelFeatureMismatch(ModelRoutingError):
    """Raised when a backend does not provide features required by a route."""


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """
    Mapping between a logical agent and a model backend.

    agent_id:
        Logical agent identifier, e.g. "safety_agent".
        Use "*" as a default fallback route.

    backend:
        Registered backend name, e.g. "claude", "aimlapi", "featherless".

    model:
        Optional model override for this route. If omitted, backend.default_model
        is used.

    required_features:
        Features required by this route. The registry validates them against
        backend.features at resolution time.

    metadata:
        Optional routing metadata for audit/debugging. Must not contain secrets.
    """

    agent_id: str
    backend: str
    model: str | None = None
    required_features: frozenset[ModelFeature] = field(default_factory=frozenset)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_id", self.agent_id.strip())
        object.__setattr__(self, "backend", self.backend.strip())

        if not self.agent_id:
            raise ValueError("ModelRoute.agent_id must not be empty")
        if not self.backend:
            raise ValueError("ModelRoute.backend must not be empty")

        if not isinstance(self.required_features, frozenset):
            object.__setattr__(
                self,
                "required_features",
                frozenset(self.required_features),
            )


@dataclass(frozen=True, slots=True)
class ModelResolution:
    """
    Concrete backend resolution for an agent.

    This object is intentionally small and provider-neutral. It can be attached
    to audit metadata without leaking secrets or provider clients.
    """

    agent_id: str
    backend: ModelBackend
    backend_name: str
    provider: str
    model: str
    route: ModelRoute

    @property
    def audit_metadata(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "backend": self.backend_name,
            "provider": self.provider,
            "model": self.model,
            "required_features": sorted(self.route.required_features),
        }


class ModelRegistry:
    """
    In-memory model backend registry.

    The registry is intentionally dependency-free. Config loading belongs in a
    later layer so fi-runner can support YAML/env/project-specific config
    without changing this core resolver.
    """

    def __init__(
        self,
        *,
        backends: Iterable[ModelBackend] | None = None,
        routes: Iterable[ModelRoute] | None = None,
        default_route_key: str = "*",
    ) -> None:
        self._backends: dict[str, ModelBackend] = {}
        self._routes: dict[str, ModelRoute] = {}
        self.default_route_key = default_route_key

        for backend in backends or ():
            self.register_backend(backend)

        for route in routes or ():
            self.register_route(route)

    @property
    def backends(self) -> Mapping[str, ModelBackend]:
        return dict(self._backends)

    @property
    def routes(self) -> Mapping[str, ModelRoute]:
        return dict(self._routes)

    def register_backend(self, backend: ModelBackend) -> None:
        """
        Register a backend by backend.name.
        """

        name = getattr(backend, "name", "").strip()
        if not name:
            raise ValueError("ModelBackend.name must not be empty")

        self._backends[name] = backend

    def register_route(self, route: ModelRoute) -> None:
        """
        Register or replace a route by route.agent_id.
        """

        self._routes[route.agent_id] = route

    def get_route(self, agent_id: str) -> ModelRoute:
        """
        Return the explicit agent route or the default "*" route.
        """

        normalized = agent_id.strip()
        if not normalized:
            raise ValueError("agent_id must not be empty")

        route = self._routes.get(normalized)
        if route is not None:
            return route

        default_route = self._routes.get(self.default_route_key)
        if default_route is not None:
            return default_route

        raise ModelRouteNotConfigured(
            f"No model route configured for agent_id={normalized!r} "
            f"and no default route {self.default_route_key!r} exists"
        )

    def resolve(self, agent_id: str) -> ModelResolution:
        """
        Resolve the backend/model for an agent.

        Raises:
            ModelRouteNotConfigured
            ModelBackendNotRegistered
            ModelFeatureMismatch
        """

        route = self.get_route(agent_id)
        backend = self._backends.get(route.backend)

        if backend is None:
            raise ModelBackendNotRegistered(
                f"Model backend {route.backend!r} is not registered "
                f"for agent_id={agent_id!r}"
            )

        backend_features = set(getattr(backend, "features", set()))
        missing_features = set(route.required_features) - backend_features

        if missing_features:
            raise ModelFeatureMismatch(
                f"Backend {route.backend!r} is missing required features "
                f"for agent_id={agent_id!r}: {sorted(missing_features)}"
            )

        model = route.model or getattr(backend, "default_model", "").strip()
        if not model:
            raise ModelRoutingError(
                f"No model configured for backend={route.backend!r}, "
                f"agent_id={agent_id!r}"
            )

        return ModelResolution(
            agent_id=agent_id,
            backend=backend,
            backend_name=route.backend,
            provider=getattr(backend, "provider", route.backend),
            model=model,
            route=route,
        )
