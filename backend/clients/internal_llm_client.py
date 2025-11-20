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

from typing import Any

import httpx

from backend.logger import get_logger

logger = get_logger(__name__)


class InternalLLMClient:
    """Cliente para llamar endpoints internos de LLM via HTTP."""

    def __init__(self, base_url: str = "http://localhost:7001"):
        """Inicializa cliente HTTP interno.

        Args:
            base_url: Base URL del backend (default: localhost:7001)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def chat(
        self,
        persona: str,
        message: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        doctor_id: str | None = None,
        use_memory: bool = False,
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
