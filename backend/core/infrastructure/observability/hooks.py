"""Observability hooks stubs.

Temporary stubs until Phase 2.2 observability extraction is completed.
These are no-op decorators that allow the code to run without actual observability.
"""

from functools import wraps
from typing import Any, Callable


def log_llm_call(func: Callable) -> Callable:
    """Stub decorator for logging LLM calls.

    TODO: Implement actual observability in Phase 2.2.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper


def log_llm_error(func: Callable) -> Callable:
    """Stub decorator for logging LLM errors.

    TODO: Implement actual observability in Phase 2.2.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)
    return wrapper
