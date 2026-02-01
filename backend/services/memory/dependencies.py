"""FastAPI Dependency Injection providers for Memory service.

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-31 (Phase 2.4 - IMemoryStore injection)
Updated: 2026-01-31 (Elasticsearch + Metrics + Cache)
Card: DI Refactor Phase 2.4 - Memory Service DI
"""

import os
from typing import Final
from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl
from backend.config import CORPUS_PATH
from backend.repositories.hdf5_memory_store import HDF5MemoryStore
from backend.repositories.interfaces.imemory_store import IMemoryStore
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.infrastructure.logging.structlog_adapter import StructlogAdapter
from backend.utils.common.logging.logger import get_logger

# Optional imports (Elasticsearch + decorators)
# Type safety: Final[bool] indicates these are constants (immutable after initialization)
try:
    from elasticsearch import Elasticsearch
    from backend.repositories.elasticsearch_memory_store import ElasticsearchMemoryStore

    ELASTICSEARCH_AVAILABLE: Final[bool] = True
except ImportError:
    ELASTICSEARCH_AVAILABLE: Final[bool] = False

try:
    from backend.repositories.metrics_memory_store import MetricsMemoryStore
    from backend.repositories.cached_memory_store import CachedMemoryStore

    DECORATORS_AVAILABLE: Final[bool] = True
except ImportError:
    DECORATORS_AVAILABLE: Final[bool] = False


class MemoryStoreConfig(BaseModel):
    """Type-safe memory store configuration with validation.

    Validation Rules:
        - use_elasticsearch: Must be bool
        - elasticsearch_url: Must be valid HTTP(S) URL if use_elasticsearch=True
        - cache_size: Must be > 0 (positive integer)

    Immutability:
        - frozen=True prevents accidental modification after initialization
        - Same behavior as @dataclass(frozen=True)

    DI Improvement:
        - Centralizes env var reading in one place
        - Makes configuration explicit (vs scattered os.getenv() calls)
        - Testable (can inject mock config in tests)
        - Fail-fast validation at startup (vs runtime errors)
    """

    use_elasticsearch: bool = Field(
        default=False,
        description="Enable Elasticsearch backend (O(log N) search)",
    )
    elasticsearch_url: HttpUrl | None = Field(
        default=None,
        description="Elasticsearch connection URL (e.g., http://localhost:9200)",
    )
    cache_size: int = Field(
        default=128,
        gt=0,  # Validation: cache_size must be > 0
        description="LRU cache size for get_audio_events()",
    )

    @field_validator("elasticsearch_url")
    @classmethod
    def validate_es_url_required(cls, v: HttpUrl | None, info) -> HttpUrl | None:
        """Ensure elasticsearch_url provided when use_elasticsearch=True.

        Args:
            v: elasticsearch_url value
            info: Validation context with other field values

        Returns:
            Validated elasticsearch_url or None

        Raises:
            ValueError: If use_elasticsearch=True but elasticsearch_url is None
        """
        if info.data.get("use_elasticsearch") and not v:
            raise ValueError("elasticsearch_url required when use_elasticsearch=True")
        return v

    model_config = ConfigDict(frozen=True)  # Immutable (same as @dataclass(frozen=True))


def get_memory_config() -> MemoryStoreConfig:
    """Get memory store configuration from environment variables.

    Environment Variables:
        USE_ELASTICSEARCH=true → Enable Elasticsearch backend
        ELASTICSEARCH_URL=http://localhost:9200 → ES connection
        MEMORY_CACHE_SIZE=128 → LRU cache size

    Returns:
        MemoryStoreConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid (e.g., cache_size <= 0)

    Note:
        Pydantic validates automatically in __init__:
        - cache_size must be > 0
        - elasticsearch_url must be valid HTTP(S) URL
        - Cross-field: elasticsearch_url required when use_elasticsearch=True
    """
    use_es = os.getenv("USE_ELASTICSEARCH", "false").lower() == "true"
    # Only read ELASTICSEARCH_URL from env (no default) to enforce validation
    es_url = os.getenv("ELASTICSEARCH_URL") if use_es else None
    cache_sz = int(os.getenv("MEMORY_CACHE_SIZE", "128"))

    return MemoryStoreConfig(
        use_elasticsearch=use_es,
        elasticsearch_url=es_url,
        cache_size=cache_sz,
    )


def get_corpus_path() -> str:
    """Get HDF5 corpus path from centralized config.

    Returns:
        Path to corpus.h5 file as string
    """
    return str(CORPUS_PATH)


def get_memory_logger() -> ILogger:
    """Get logger for memory service.

    Returns:
        ILogger instance (StructlogAdapter wrapping BoundLogger)

    Type Safety:
        - get_logger() returns structlog.BoundLogger
        - StructlogAdapter wraps BoundLogger to implement ILogger
        - Fixes Pyright type mismatch warning
    """
    bound_logger = get_logger("memory")
    return StructlogAdapter(bound_logger)


def get_memory_store(config: MemoryStoreConfig | None = None) -> IMemoryStore:
    """Get memory store implementation with feature flag support.

    DI Improvement:
        - Config injected instead of reading os.getenv() directly
        - Testable (can inject mock config in tests)
        - Centralizes env var reading in get_memory_config()

    Feature Flag (from config):
        use_elasticsearch=True → ElasticsearchMemoryStore (O(log N) search)
        use_elasticsearch=False (default) → HDF5MemoryStore (O(N) search)

    Decorators (always applied if available):
        - MetricsMemoryStore → Latency/error tracking
        - CachedMemoryStore → LRU cache for get_audio_events()

    Args:
        config: Memory store configuration (defaults to get_memory_config())

    Returns:
        IMemoryStore instance (HDF5 or Elasticsearch + Metrics + Cache)

    Clean Architecture:
        Router → DIMemoryService → IMemoryStore (interface)
            ↓
        Cache(Metrics(Elasticsearch/HDF5)) ← Decorator stack
    """
    # Default config from env vars if not provided
    if config is None:
        config = get_memory_config()

    logger = get_memory_logger()

    # Feature flag: Elasticsearch vs HDF5
    if config.use_elasticsearch and ELASTICSEARCH_AVAILABLE:
        # Production: Elasticsearch (O(log N) search)
        logger.info(
            "MEMORY_STORE_INIT",
            implementation="elasticsearch",
            url=config.elasticsearch_url,
        )

        try:
            es_client = Elasticsearch([config.elasticsearch_url])
            store: IMemoryStore = ElasticsearchMemoryStore(
                es_client=es_client,
                logger=logger,
            )
        except Exception as e:
            logger.error(
                "ELASTICSEARCH_INIT_ERROR",
                error=str(e),
                fallback="hdf5",
            )
            # Fallback to HDF5 on Elasticsearch failure
            store = HDF5MemoryStore(
                corpus_path=get_corpus_path(),
                logger=logger,
            )
    else:
        # Development: HDF5 (O(N) search)
        logger.info(
            "MEMORY_STORE_INIT",
            implementation="hdf5",
            corpus_path=get_corpus_path(),
        )
        store = HDF5MemoryStore(
            corpus_path=get_corpus_path(),
            logger=logger,
        )

    # Apply decorators (if available)
    if DECORATORS_AVAILABLE:
        # Add metrics tracking
        store = MetricsMemoryStore(delegate=store, logger=logger)
        logger.debug("MEMORY_STORE_DECORATOR", decorator="metrics")

        # Add LRU cache (from config)
        store = CachedMemoryStore(delegate=store, cache_size=config.cache_size, logger=logger)
        logger.debug("MEMORY_STORE_DECORATOR", decorator="cache", cache_size=config.cache_size)

    return store


def get_memory_service() -> DIMemoryService:
    """Get memory service with injected dependencies.

    FastAPI provider for DIMemoryService.

    Returns:
        DIMemoryService instance with memory_store and logger

    Clean Architecture:
        Router → DIMemoryService (business logic) → IMemoryStore (interface) → HDF5MemoryStore (implementation)
    """
    return DIMemoryService(
        memory_store=get_memory_store(),
        logger=get_memory_logger(),
    )
