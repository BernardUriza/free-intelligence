"""
fi_runner.models.providers

Thin provider-specific wrappers around OpenAICompatibleBackend.

These classes intentionally do not read environment variables, ~/.secrets, or
project config files. They only receive explicit constructor arguments.

Config loading belongs in a separate layer.
"""

from __future__ import annotations

from typing import Any

from .contracts import ModelFeature
from .openai_compatible import OpenAICompatibleBackend


class AimlAPIBackend(OpenAICompatibleBackend):
    """
    AI/ML API backend.

    AI/ML API is treated as an OpenAI-compatible chat completion provider.
    This wrapper exists so audit logs and registry config can refer to a stable
    backend type/name without hardcoding provider plumbing inside agents.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        name: str = "aimlapi",
        provider: str = "aimlapi",
        features: set[ModelFeature] | None = None,
        client: Any | None = None,
        supports_json_object: bool = True,
        supports_json_schema: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            features=features,
            client=client,
            supports_json_object=supports_json_object,
            supports_json_schema=supports_json_schema,
        )


class FeatherlessBackend(OpenAICompatibleBackend):
    """
    Featherless backend.

    Featherless is treated as an OpenAI-compatible chat completion provider.
    This wrapper keeps provider identity explicit while reusing the common
    OpenAICompatibleBackend implementation.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        name: str = "featherless",
        provider: str = "featherless",
        features: set[ModelFeature] | None = None,
        client: Any | None = None,
        supports_json_object: bool = True,
        supports_json_schema: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            features=features,
            client=client,
            supports_json_object=supports_json_object,
            supports_json_schema=supports_json_schema,
        )
