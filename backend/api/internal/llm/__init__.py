"""
Internal LLM API - Free Intelligence

CRITICAL: Estos endpoints son INTERNOS.
- Middleware InternalOnlyMiddleware bloquea acceso externo
- Solo accesibles vía HTTP interno desde workflows públicos
- Proveen ultra observabilidad de TODAS las interacciones LLM

Propósito:
- Centralizar lógica de LLM
- Logging ultra detallado (prompts, responses, tokens, timing)
- Audit trail completo con hashes
- Gestión de "personas" (modos del asistente)

Endpoints:
- POST /chat → Conversación libre con Free-Intelligence
- POST /structured-extract → Extracción estructurada (JSON)
- POST /soap-edit → SOAP modification (legacy wrapper)
"""

from .router import router

__all__ = ["router"]
