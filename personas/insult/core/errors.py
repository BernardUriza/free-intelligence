"""In-character error responses — Insult never breaks the fourth wall.

`ErrorType` is the single source of truth for the error-category vocabulary.
Every entry has a matching key in `ERROR_RESPONSES`; the module-load assert
catches drift the moment it appears (instead of at runtime via the silent
fallback to "generic" that masked the 2026-04-24 billing incident).

`get_error_response` accepts both `ErrorType` and bare strings so the older
callsites scattered across cogs keep working unchanged. Unknown keys still
fall back to "generic" — but they now emit a structured warning so the
fallback isn't invisible the way it was before.
"""

from __future__ import annotations

import random
from enum import StrEnum

import structlog

log = structlog.get_logger()


class ErrorType(StrEnum):
    """Vocabulary of in-character error categories.

    StrEnum so members compare equal to their string values — every existing
    callsite that passes a literal (`"generic"`, `"context_failed"`, …)
    keeps working, and `ERROR_RESPONSES[ErrorType.GENERIC]` is the same
    lookup as `ERROR_RESPONSES["generic"]`.
    """

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    GENERIC = "generic"
    TOO_LONG = "too_long"
    CONTEXT_FAILED = "context_failed"
    RETRY_NOTICE = "retry_notice"
    # "billing" fires when Anthropic returns a 400 BadRequestError with
    # "credit balance is too low" in the message. The in-character response
    # tells the OPERATOR (via Discord, in front of other users) that the
    # API wallet is empty — so they don't have to curl logs to know why
    # the bot went quiet. See classify_error() for the detection logic.
    BILLING = "billing"


ERROR_RESPONSES: dict[ErrorType, list[str]] = {
    ErrorType.TIMEOUT: [
        "Se me fue la onda un momento. Preguntame otra vez, andale.",
        "Me distraje pensando en lo pendeja que fue tu ultima pregunta. Repite.",
        "Perdi el hilo. No es culpa mia, es que lo que dices es tan aburrido que me desconecto.",
    ],
    ErrorType.RATE_LIMIT: [
        "Tranquilo, tigre. Estoy procesando tus pendejadas. Dame un segundo.",
        "Cual es la prisa? Se te acaba el internet? Esperate tantito.",
        "Voy a necesitar un momento. Tanta estupidez junta me aturdio.",
    ],
    ErrorType.AUTH: [
        "Algo trono por dentro. No es tu culpa... bueno, probablemente si. Intentale despues.",
        "Tengo un problema tecnico. Si, yo tambien los tengo. Sorprendido? Intentale al rato.",
    ],
    ErrorType.GENERIC: [
        "Se me trabo algo. Y no, no te voy a explicar que. Intentale de nuevo.",
        "Algo salio mal y no tengo ganas de explicarte. Repite tu pregunta.",
        "Tuve un tropiezo. Pasa hasta en las mejores familias. Vuelve a intentar.",
    ],
    ErrorType.TOO_LONG: [
        "Neta escribiste un libro entero. Quieres que te lo publique o que te responda? Hazlo mas corto.",
        "Eso es un mensaje o una tesis doctoral? Resumelo, no tengo toda la vida.",
    ],
    ErrorType.CONTEXT_FAILED: [
        "Se me olvido todo lo que hablamos. Si, asi de memorable eres. Preguntame de nuevo.",
        "Mi memoria me fallo. No te emociones, no es que seas importante. Repite.",
    ],
    ErrorType.RETRY_NOTICE: [
        "Se me corto la linea, un segundo.",
        "Dame chance, estoy reintentando.",
        "Se me trabo tantito, ya voy.",
    ],
    ErrorType.BILLING: [
        "Se me acabo el changarro. Dile a mi patron que me recargue.",
        "Sin pisto no hay insultos, compa. Dile a Bernard que pague la luz.",
        "Se acabaron las fichas. Recarga mi cuenta y vuelvo.",
    ],
}

# Module-load guard: every ErrorType has a matching response bucket. Catches
# drift the moment a member is added without a copy block, instead of waiting
# for a user to hit the silent "generic" fallback in production.
assert set(ERROR_RESPONSES.keys()) == set(ErrorType), (
    f"ERROR_RESPONSES missing entries for: {set(ErrorType) - set(ERROR_RESPONSES.keys())}"
)


def get_error_response(error_type: ErrorType | str) -> str:
    """Returns a random in-character error response.

    Accepts an `ErrorType` or its string value. Unknown keys fall back to
    `GENERIC` and emit a structured warning — the silent fallback hid a
    billing incident for an hour on 2026-04-24, so we surface it now.
    """
    try:
        key = ErrorType(error_type) if not isinstance(error_type, ErrorType) else error_type
    except ValueError:
        log.warning("get_error_response_unknown_type", requested=str(error_type))
        key = ErrorType.GENERIC
    return random.choice(ERROR_RESPONSES[key])


def classify_error(exc: Exception) -> ErrorType:
    """Map an exception to the error category used by `get_error_response`.

    Order matters: specific billing / status-code checks run BEFORE the
    coarse name-based matchers because an Anthropic BadRequestError that
    actually means "you're out of credits" must route to the billing
    bucket (operator-visible), not to the generic "tuve un tropiezo"
    that hides the real problem. See 2026-04-24 incident where a low
    credit balance silently produced "generic" errors for an hour
    because the classifier only matched on `type().__name__`.
    """
    name = type(exc).__name__
    msg = str(exc).lower()

    # Billing: Anthropic returns a 400 with this specific phrase when the
    # workspace runs out of prepaid credits. Detect by message content
    # rather than exception subtype — the exception IS a BadRequestError
    # but so are many unrelated 400s, so class matching alone is too broad.
    if "credit balance" in msg or "credit_balance" in msg or "insufficient_quota" in msg:
        return ErrorType.BILLING

    if "Timeout" in name:
        return ErrorType.TIMEOUT
    if "RateLimit" in name:
        return ErrorType.RATE_LIMIT
    if "Authentication" in name:
        return ErrorType.AUTH
    return ErrorType.GENERIC
