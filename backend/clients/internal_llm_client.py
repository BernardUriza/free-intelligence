"""
Internal LLM Client - HTTP wrapper para llamar /internal/llm

Este cliente abstrae las llamadas HTTP internas a los endpoints de LLM.
Proporciona una interfaz limpia para workflows públicos.

Arquitectura:
    Public Workflow → InternalLLMClient → HTTP → /internal/llm → LLM Router → Claude/etc

Ventajas:
- Desacoplamiento: Workflows no llaman directamente a LLM
- Observabilidad: Logs ultra detallados en capa internal
- Consistencia: Todos los workflows usan mismo client
- Testeable: Fácil mockear en tests
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import httpx
import os
from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


class InternalLLMClient:
    """Cliente para llamar endpoints internos de LLM via HTTP."""

    def __init__(self, base_url: str = "http://localhost:7001"):
        """Inicializa cliente HTTP interno.

        Args:
            base_url: Base URL del backend (default: localhost:7001)
        """
        self.base_url = base_url
        # Timeout config: must be longer than LLM inference time
        # Local models like Qwen3 can take 60-120 seconds on CPU
        # Frontend timeout is 120s, so backend must match or exceed it
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=10.0),  # 3 min read timeout
        )

    async def chat(
        self,
        persona: str,
        message: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        doctor_id: str | None = None,
        use_memory: bool = False,
        request_id: str | None = None,
        trace_id: str | None = None,
        caller: str = "public",
    ) -> dict:
        """Conversación con Free-Intelligence.

        Args:
            persona: Modo del asistente (onboarding_guide, clinical_advisor, etc.)
            message: Mensaje del usuario
            context: Contexto adicional (patient_id, session_id, etc.)
            session_id: Session ID para audit
            doctor_id: Doctor ID para memoria conversacional
            use_memory: Enable conversation memory (requires doctor_id)

        Returns:
            {
                "response": str,
                "persona": str,
                "tokens_used": int,
                "latency_ms": int,
                "model": str,
                "prompt_hash": str,
                "response_hash": str,
                "logged_at": str
            }

        Raises:
            httpx.HTTPStatusError: Si la llamada falla
        """
        try:
            logger.debug(
                "INTERNAL_LLM_CLIENT_CHAT_START",
                persona=persona,
                message_length=len(message),
                has_context=context is not None,
                session_id=session_id,
            )

            headers = {}
            if request_id:
                headers["x-fi-request-id"] = request_id
            if trace_id:
                headers["x-fi-trace-id"] = trace_id

            # Security guard: if enforcement enabled, raise; otherwise warn.
            if caller != "internal":
                logger.warning(
                    "SECURITY_GUARD_CHECK",
                    reason="non_internal_caller",
                    caller=caller,
                )
                if os.getenv("FI_ENFORCE_GUARD", "0") == "1":
                    logger.error("SECURITY_GUARD_HIT", caller=caller)
                    raise AssertionError("Public layer must not call internal endpoints directly")

            response = await self.client.post(
                "/internal/llm/chat",
                json={
                    "persona": persona,
                    "message": message,
                    "context": context,
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "use_memory": use_memory,
                },
                headers=headers or None,
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(
                "INTERNAL_LLM_CLIENT_CHAT_SUCCESS",
                persona=persona,
                tokens=data.get("tokens_used"),
                latency=data.get("latency_ms"),
                session_id=session_id,
            )

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_CHAT_HTTP_ERROR",
                persona=persona,
                status_code=e.response.status_code,
                error=str(e),
                session_id=session_id,
            )
            raise
        except Exception as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_CHAT_FAILED",
                persona=persona,
                error=str(e),
                error_type=type(e).__name__,
                session_id=session_id,
            )
            raise

    async def chat_stream(
        self,
        persona: str,
        message: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        doctor_id: str | None = None,
        use_memory: bool = False,
        request_id: str | None = None,
        trace_id: str | None = None,
        caller: str = "public",
    ) -> AsyncGenerator[str]:
        """Streaming chat - yields content chunks as they arrive.

        Streams Server-Sent Events (SSE) from /internal/llm/chat/stream.

        Args:
            persona: Modo del asistente
            message: Mensaje del usuario
            context: Contexto adicional
            session_id: Session ID para audit
            doctor_id: Doctor ID para memoria conversacional
            use_memory: Enable conversation memory
            request_id: Request ID para tracing
            trace_id: Trace ID para distributed tracing
            caller: Caller identifier (public/internal)

        Yields:
            str: Content chunks as they arrive from the LLM

        Raises:
            httpx.HTTPStatusError: Si la llamada falla
        """
        try:
            logger.debug(
                "INTERNAL_LLM_CLIENT_CHAT_STREAM_START",
                persona=persona,
                message_length=len(message),
                has_context=context is not None,
                session_id=session_id,
            )

            headers = {}
            if request_id:
                headers["x-fi-request-id"] = request_id
            if trace_id:
                headers["x-fi-trace-id"] = trace_id

            # Security guard check
            if caller != "internal":
                logger.warning(
                    "SECURITY_GUARD_CHECK_STREAM",
                    reason="non_internal_caller",
                    caller=caller,
                )
                if os.getenv("FI_ENFORCE_GUARD", "0") == "1":
                    logger.error("SECURITY_GUARD_HIT_STREAM", caller=caller)
                    raise AssertionError("Public layer must not call internal endpoints directly")

            # Use stream=True for SSE streaming
            async with self.client.stream(
                "POST",
                "/internal/llm/chat/stream",
                json={
                    "persona": persona,
                    "message": message,
                    "context": context,
                    "session_id": session_id,
                    "doctor_id": doctor_id,
                    "use_memory": use_memory,
                },
                headers=headers or None,
            ) as response:
                response.raise_for_status()

                # Parse SSE stream
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    try:
                        import json
                        chunk_data = json.loads(line[6:])  # Remove "data: " prefix

                        # Check for error or completion markers
                        if "error" in chunk_data:
                            logger.error(
                                "STREAM_ERROR",
                                persona=persona,
                                error=chunk_data.get("error"),
                            )
                            yield f"ERROR: {chunk_data.get('error')}"
                            break

                        if chunk_data.get("done"):
                            logger.debug(
                                "STREAM_COMPLETED",
                                persona=persona,
                                session_id=session_id,
                            )
                            break

                        # Yield content chunk
                        content = chunk_data.get("content", "")
                        if content:
                            yield content

                    except json.JSONDecodeError:
                        logger.warning(
                            "STREAM_JSON_PARSE_ERROR",
                            line=line[:100],
                        )
                        continue

        except httpx.HTTPStatusError as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_CHAT_STREAM_HTTP_ERROR",
                persona=persona,
                status_code=e.response.status_code,
                error=str(e),
                session_id=session_id,
            )
            raise
        except Exception as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_CHAT_STREAM_FAILED",
                persona=persona,
                error=str(e),
                error_type=type(e).__name__,
                session_id=session_id,
            )
            raise

    async def structured_extract(
        self,
        persona: str,
        command: str,
        context: dict[str, Any],
        output_schema: dict[str, str],
        session_id: str | None = None,
    ) -> dict:
        """Extracción estructurada (JSON) via LLM.

        Args:
            persona: Modo del asistente
            command: Comando en lenguaje natural
            context: Contexto necesario (ej: current_soap)
            output_schema: Schema esperado del JSON {"field": "type"}
            session_id: Session ID para audit

        Returns:
            {
                "data": dict,
                "explanation": str,
                "tokens_used": int,
                "latency_ms": int,
                "model": str,
                "prompt_hash": str,
                "response_hash": str,
                "logged_at": str
            }

        Raises:
            httpx.HTTPStatusError: Si la llamada falla
        """
        try:
            logger.debug(
                "INTERNAL_LLM_CLIENT_STRUCTURED_START",
                persona=persona,
                command_length=len(command),
                schema_fields=list(output_schema.keys()),
                session_id=session_id,
            )

            response = await self.client.post(
                "/internal/llm/structured-extract",
                json={
                    "persona": persona,
                    "command": command,
                    "context": context,
                    "output_schema": output_schema,
                    "session_id": session_id,
                },
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(
                "INTERNAL_LLM_CLIENT_STRUCTURED_SUCCESS",
                persona=persona,
                tokens=data.get("tokens_used"),
                latency=data.get("latency_ms"),
                data_fields=list(data.get("data", {}).keys()),
                session_id=session_id,
            )

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_STRUCTURED_HTTP_ERROR",
                persona=persona,
                status_code=e.response.status_code,
                error=str(e),
                session_id=session_id,
            )
            raise
        except Exception as e:
            logger.error(
                "INTERNAL_LLM_CLIENT_STRUCTURED_FAILED",
                persona=persona,
                error=str(e),
                error_type=type(e).__name__,
                session_id=session_id,
            )
            raise

    async def close(self):
        """Cierra el cliente HTTP."""
        await self.client.aclose()

    async def __aenter__(self):
        """Context manager support."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        await self.close()


# ============================================================================
# Singleton instance
# ============================================================================

_llm_client: InternalLLMClient | None = None


def get_llm_client() -> InternalLLMClient:
    """Get singleton instance of internal LLM client.

    Returns:
        Shared InternalLLMClient instance

    Example:
        >>> client = get_llm_client()
        >>> result = await client.chat(persona="onboarding_guide", message="Hi!")
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = InternalLLMClient()
    return _llm_client
