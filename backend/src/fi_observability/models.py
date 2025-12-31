# fi_observability/models.py
# Data models for LLM call logging

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CallStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class LLMCallCreate:
    """Data required to log an LLM call."""

    model: str
    provider: str  # ollama, azure, claude, etc.

    # Tokens
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # Timing
    latency_ms: int = 0

    # Status
    status: CallStatus = CallStatus.SUCCESS
    error_message: Optional[str] = None

    # Content previews (for debugging, not full content)
    prompt_preview: str = ""  # First 500 chars
    response_preview: str = ""  # First 500 chars

    # Context
    client_id: Optional[str] = None  # User/doctor ID
    session_id: Optional[str] = None
    persona: Optional[str] = None  # general_assistant, soap_generator, etc.

    # Hashes for dedup/lookup (from existing logging)
    prompt_hash: Optional[str] = None
    response_hash: Optional[str] = None

    # Extra metadata
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["metadata"] = json.dumps(self.metadata) if self.metadata else "{}"
        return d


@dataclass
class LLMCall(LLMCallCreate):
    """Full LLM call record with ID and timestamp."""

    id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_row(cls, row: dict) -> "LLMCall":
        """Create LLMCall from database row."""
        return cls(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"],
            model=row["model"],
            provider=row["provider"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            latency_ms=row["latency_ms"],
            status=CallStatus(row["status"]),
            error_message=row.get("error_message"),
            prompt_preview=row.get("prompt_preview", ""),
            response_preview=row.get("response_preview", ""),
            client_id=row.get("client_id"),
            session_id=row.get("session_id"),
            persona=row.get("persona"),
            prompt_hash=row.get("prompt_hash"),
            response_hash=row.get("response_hash"),
            metadata=json.loads(row.get("metadata", "{}")) if row.get("metadata") else {},
        )


@dataclass
class CallStats:
    """Aggregated statistics for LLM calls."""

    total_calls: int = 0
    success_calls: int = 0
    error_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    # By model
    calls_by_model: dict = field(default_factory=dict)

    # By client
    calls_by_client: dict = field(default_factory=dict)


@dataclass
class ClientReport:
    """Report for a specific client."""

    client_id: str
    period_start: datetime
    period_end: datetime

    total_calls: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    calls_by_model: dict = field(default_factory=dict)
    calls_by_persona: dict = field(default_factory=dict)

    avg_latency_ms: float = 0.0
    error_rate: float = 0.0

    # Cost estimation (configurable per model)
    estimated_cost_usd: float = 0.0

    # Top calls
    recent_calls: list = field(default_factory=list)
