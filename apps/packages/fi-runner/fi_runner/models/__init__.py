"""
fi_runner.models

Provider-agnostic model backend layer for fi-runner.

This package lets workflow agents request model capabilities without knowing
which provider executes the call.
"""

from .audit import (
    ModelAuditEvent,
    ModelAuditEventType,
    model_call_completed_event,
    model_call_failed_event,
    model_call_started_event,
)
from .config import (
    ModelRegistryConfig,
    ModelRegistryConfigError,
    build_model_registry,
    build_model_registry_from_mapping,
)
from .context import (
    RunnerContext,
    RunnerContextError,
)
from .contracts import (
    ModelBackend,
    ModelDelta,
    ModelFeature,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelRole,
    ModelUsage,
)
from .factory import (
    BackendType,
    ModelBackendConfig,
    ModelBackendConfigError,
    build_model_backend,
)
from .openai_compatible import OpenAICompatibleBackend
from .providers import (
    AimlAPIBackend,
    FeatherlessBackend,
)
from .registry import (
    ModelBackendNotRegistered,
    ModelFeatureMismatch,
    ModelRegistry,
    ModelResolution,
    ModelRoute,
    ModelRouteNotConfigured,
    ModelRoutingError,
)

__all__ = [
    "ModelAuditEvent",
    "ModelAuditEventType",
    "model_call_completed_event",
    "model_call_failed_event",
    "model_call_started_event",
    "ModelRegistryConfig",
    "ModelRegistryConfigError",
    "build_model_registry",
    "build_model_registry_from_mapping",
    "RunnerContext",
    "RunnerContextError",
    "ModelBackend",
    "ModelDelta",
    "ModelFeature",
    "ModelMessage",
    "ModelRequest",
    "ModelResponse",
    "ModelRole",
    "ModelUsage",
    "BackendType",
    "ModelBackendConfig",
    "ModelBackendConfigError",
    "build_model_backend",
    "OpenAICompatibleBackend",
    "AimlAPIBackend",
    "FeatherlessBackend",
    "ModelBackendNotRegistered",
    "ModelFeatureMismatch",
    "ModelRegistry",
    "ModelResolution",
    "ModelRoute",
    "ModelRouteNotConfigured",
    "ModelRoutingError",
]
