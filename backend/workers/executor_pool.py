"""Global ThreadPoolExecutor for background worker tasks.

PHILOSOPHY:
  - Single shared executor instance (prevents GC of threads)
  - Persists across multiple requests
  - Properly configured for CPU-bound (transcription) tasks
  - Non-blocking futures that execute independently

Architecture:
  Service → spawn_worker() → executor.submit() → worker function runs independently

Created: 2025-11-15
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from backend.logger import get_logger

logger = get_logger(__name__)

# Global executor instance (singleton pattern)
_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def get_executor() -> ThreadPoolExecutor:
    """Get or create global ThreadPoolExecutor.

    Thread-safe singleton that persists across requests.
    Prevents thread garbage collection by maintaining a reference.

    Returns:
        ThreadPoolExecutor instance with 4 workers
    """
    global _executor

    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=1,  # DEMO MODE: 1 worker to prevent HDF5 concurrency errors
                    thread_name_prefix="fi-worker-",
                )
                logger.info(
                    "EXECUTOR_POOL_INITIALIZED",
                    max_workers=1,
                    thread_prefix="fi-worker-",
                )

    return _executor


def spawn_worker(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Spawn a background worker task (fire-and-forget).

    Args:
        func: Callable function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        None (fire-and-forget pattern)

    Example:
        ```python
        spawn_worker(transcribe_chunk_worker, session_id='abc', chunk_number=0)
        # Worker executes asynchronously without blocking
        ```
    """
    executor = get_executor()

    # Submit and don't wait
    future = executor.submit(func, *args, **kwargs)

    # Add callback to log completion/errors (without blocking)
    def log_completion(f: Any) -> None:
        try:
            f.result(timeout=0.1)  # Don't block - result not used, just check for errors
            logger.debug("WORKER_COMPLETED", worker=func.__name__)
        except Exception as e:
            logger.error(
                "WORKER_FAILED",
                worker=func.__name__,
                error=str(e),
                exc_info=True,
            )

    future.add_done_callback(log_completion)


def shutdown_executor() -> None:
    """Shutdown executor gracefully (call on app shutdown).

    Used by FastAPI lifespan events.
    """
    global _executor

    if _executor is not None:
        logger.info("EXECUTOR_SHUTDOWN_STARTED")
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("EXECUTOR_SHUTDOWN_COMPLETE")
