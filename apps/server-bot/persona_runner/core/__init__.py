"""Runner core — config, wire schemas, auth. Zero SDK, zero I/O."""

from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import (
    JudgeRequest,
    JudgeResponse,
    RuleRequest,
    TurnRequest,
    TurnResponse,
)

__all__ = [
    "JudgeRequest",
    "JudgeResponse",
    "RuleRequest",
    "TurnRequest",
    "TurnResponse",
    "check_auth",
]
