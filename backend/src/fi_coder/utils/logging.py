from __future__ import annotations

import re
import structlog

from ..config.policies import LOGGING_POLICY


def get_logger(name: str):
    """Get structured logger."""
    return structlog.get_logger(name)


def redact_logs(text: str) -> str:
    """Redact sensitive information from logs."""
    for pattern in LOGGING_POLICY["redact_patterns"]:
        text = re.sub(pattern, "[REDACTED]", text)
    return text
