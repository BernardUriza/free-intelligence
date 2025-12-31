# fi_observability - LLM Call Observability for FI Edge
# Persists all LLM calls to SQLite for monitoring and reporting

from fi_observability.models import LLMCall, LLMCallCreate, CallStatus, CallStats, ClientReport
from fi_observability.logger import LLMLogger, get_llm_logger
from fi_observability.database import init_observability_db, get_db_stats, cleanup_old_records
from fi_observability.hooks import log_llm_call, log_llm_error

__all__ = [
    # Models
    "LLMCall",
    "LLMCallCreate",
    "CallStatus",
    "CallStats",
    "ClientReport",
    # Logger
    "LLMLogger",
    "get_llm_logger",
    # Database
    "init_observability_db",
    "get_db_stats",
    "cleanup_old_records",
    # Hooks (easy integration)
    "log_llm_call",
    "log_llm_error",
]
