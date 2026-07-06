"""
fi_runner.models.openai_compatible

Reusable OpenAI-compatible model backend.

This backend is intended for providers that expose an OpenAI-compatible
chat.completions API, including AI/ML API and Featherless.

Design rules:
    - Provider clients stay inside fi-runner.
    - Agents never instantiate provider SDKs directly.
    - Domain workflow contracts stay separate from model provider details.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from .contracts import (
    ModelDelta,
    ModelFeature,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)


class OpenAICompatibleBackend:
    """
    OpenAI-compatible chat completion backend.

    The OpenAI SDK import is lazy so fi-runner can expose provider contracts
    without requiring OpenAI dependencies until this backend is instantiated.

    Args:
        name:
            Registry backend name, e.g. "aimlapi" or "featherless".
        provider:
            Provider label for audit metadata.
        api_key:
            Provider API key.
        base_url:
            OpenAI-compatible API base URL.
        default_model:
            Default model for requests that do not specify one.
        features:
            Backend capabilities. Defaults to chat/json/streaming.
        client:
            Optional injected client for tests. Must expose
            client.chat.completions.create(...).
        supports_json_object:
            Whether to use response_format={"type": "json_object"} for JSON.
        supports_json_schema:
            Whether to use response_format={"type": "json_schema", ...}.
            Disabled by default because OpenAI-compatible providers vary.
    """

    def __init__(
        self,
        *,
        name: str,
        provider: str,
        api_key: str,
        base_url: str,
        default_model: str,
        features: set[ModelFeature] | None = None,
        client: Any | None = None,
        supports_json_object: bool = True,
        supports_json_schema: bool = False,
    ) -> None:
        self.name = name.strip()
        self.provider = provider.strip()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model.strip()
        self.features = features or {"chat", "json", "streaming"}

        self.supports_json_object = supports_json_object
        self.supports_json_schema = supports_json_schema

        if not self.name:
            raise ValueError("OpenAICompatibleBackend.name must not be empty")
        if not self.provider:
            raise ValueError("OpenAICompatibleBackend.provider must not be empty")
        if not self.default_model:
            raise ValueError("OpenAICompatibleBackend.default_model must not be empty")

        self.client = client if client is not None else self._build_client()

    def _build_client(self) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAICompatibleBackend requires the 'openai' package. "
                "Install it in fi-runner dependencies before using this backend."
            ) from exc

        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """
        Execute a non-streaming chat completion.
        """

        model = request.model or self.default_model
        metadata: dict[str, Any] = {}

        kwargs = self._build_completion_kwargs(
            request=request,
            model=model,
            stream=False,
        )

        result = await self.client.chat.completions.create(**kwargs)

        content = self._extract_message_content(result)
        finish_reason = self._extract_finish_reason(result)
        usage = self._extract_usage(result)

        parsed: dict[str, Any] | list[Any] | None = None
        if request.response_format == "json":
            try:
                parsed = self._parse_json_content(content)
            except Exception as exc:  # intentionally broad: preserve raw response
                metadata["json_parse_error"] = str(exc)

        return ModelResponse(
            provider=self.provider,
            model=model,
            content=content,
            parsed=parsed,
            finish_reason=finish_reason,
            usage=usage,
            raw=self._safe_model_dump(result),
            metadata=metadata,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelDelta]:
        """
        Execute a streaming chat completion.
        """

        model = request.model or self.default_model

        kwargs = self._build_completion_kwargs(
            request=request,
            model=model,
            stream=True,
        )

        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = self._extract_delta_content(chunk)
            if delta:
                yield ModelDelta(
                    provider=self.provider,
                    model=model,
                    delta=delta,
                )

    async def healthcheck(self) -> bool:
        """
        Lightweight configuration check.

        This intentionally avoids a network call. Full live-provider checks
        should be implemented in application-level diagnostics to avoid
        spending credits during imports or local smoke tests.
        """

        return bool(self.api_key and self.base_url and self.default_model)

    def _build_completion_kwargs(
        self,
        *,
        request: ModelRequest,
        model: str,
        stream: bool,
    ) -> dict[str, Any]:
        messages = list(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [self._to_provider_message(message) for message in messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

        if request.tools:
            kwargs["tools"] = request.tools

        if request.response_format == "json":
            response_format = self._build_response_format(request)
            if response_format is not None:
                kwargs["response_format"] = response_format
            else:
                kwargs["messages"] = [
                    self._to_provider_message(
                        ModelMessage(
                            role="system",
                            content=(
                                "Return only valid JSON. Do not include markdown, "
                                "code fences, commentary, or trailing explanation."
                            ),
                        )
                    ),
                    *kwargs["messages"],
                ]

        return kwargs

    def _build_response_format(self, request: ModelRequest) -> dict[str, Any] | None:
        if request.response_format != "json":
            return None

        if self.supports_json_schema and request.json_schema:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{request.agent_id}_{request.purpose}",
                    "schema": request.json_schema,
                    "strict": False,
                },
            }

        if self.supports_json_object:
            return {"type": "json_object"}

        return None

    def _to_provider_message(self, message: ModelMessage) -> dict[str, Any]:
        role = message.role
        content = message.content

        # Many OpenAI-compatible providers do not support "developer".
        if role == "developer":
            role = "system"

        # Tool messages require provider-specific tool_call_id handling.
        # Keep the minimal model backend conservative for now.
        if role == "tool":
            role = "user"
            content = f"[tool]\n{content}"

        payload: dict[str, Any] = {
            "role": role,
            "content": content,
        }

        if message.name:
            payload["name"] = message.name

        return payload

    def _extract_message_content(self, result: Any) -> str:
        choice = result.choices[0]
        message = choice.message
        content = getattr(message, "content", "") or ""
        return self._coerce_content_to_text(content)

    def _extract_delta_content(self, chunk: Any) -> str:
        if not getattr(chunk, "choices", None):
            return ""

        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        content = getattr(delta, "content", "") if delta is not None else ""
        return self._coerce_content_to_text(content or "")

    def _extract_finish_reason(self, result: Any) -> str | None:
        try:
            return result.choices[0].finish_reason
        except Exception:
            return None

    def _extract_usage(self, result: Any) -> ModelUsage | None:
        usage = getattr(result, "usage", None)
        if usage is None:
            return None

        return ModelUsage(
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )

    def _safe_model_dump(self, obj: Any) -> dict[str, Any] | None:
        try:
            if hasattr(obj, "model_dump"):
                dumped = obj.model_dump()
                return dumped if isinstance(dumped, dict) else None
        except Exception:
            return None

        return None

    def _parse_json_content(self, content: str) -> dict[str, Any] | list[Any]:
        candidate = content.strip()

        if candidate.startswith("```"):
            candidate = self._strip_markdown_fence(candidate)

        parsed = json.loads(candidate)

        if not isinstance(parsed, (dict, list)):
            raise ValueError("JSON response must parse to an object or array")

        return parsed

    def _strip_markdown_fence(self, content: str) -> str:
        lines = content.strip().splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()

    def _coerce_content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)

        return str(content)
