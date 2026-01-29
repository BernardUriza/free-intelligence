"""Dependency validation helpers for DI constructors.

Provides runtime validation to ensure injected dependencies implement expected interfaces.
Fails fast with clear error messages instead of cryptic AttributeErrors.

Author: Claude Code
Created: 2026-01-29
Purpose: DI Refactor Fix #2 - Constructor validation
"""
from typing import Any, Type


def validate_dependency(
    obj: Any,
    interface: Type,
    name: str,
    allow_none: bool = False,
) -> None:
    """Validate injected dependency implements expected interface.

    Args:
        obj: The injected object to validate
        interface: The expected interface (ABC or base class)
        name: Dependency name for error messages (e.g., "task_repository")
        allow_none: If True, None is acceptable (for optional dependencies)

    Raises:
        ValueError: If obj is None and allow_none=False
        TypeError: If obj doesn't implement the interface

    Example:
        >>> from backend.repositories.interfaces import ITaskRepository
        >>>
        >>> class MyService:
        ...     def __init__(self, task_repo: ITaskRepository):
        ...         validate_dependency(task_repo, ITaskRepository, "task_repo")
        ...         self.task_repo = task_repo
        >>>
        >>> # Valid:
        >>> service = MyService(HDF5TaskRepository(...))  # ✅
        >>>
        >>> # Invalid:
        >>> service = MyService(None)  # ❌ ValueError: task_repo cannot be None
        >>> service = MyService("wrong")  # ❌ TypeError: task_repo must implement ITaskRepository
    """
    # Check for None
    if obj is None:
        if allow_none:
            return  # None is acceptable
        raise ValueError(
            f"{name} cannot be None. "
            f"Expected instance implementing {interface.__name__}."
        )

    # Check interface compliance
    if not isinstance(obj, interface):
        raise TypeError(
            f"{name} must implement {interface.__name__}, "
            f"got {type(obj).__name__} instead.\n"
            f"Hint: Ensure the injected object inherits from {interface.__name__}."
        )


def validate_dependencies(**kwargs: dict[str, tuple[Any, Type, bool]]) -> None:
    """Validate multiple dependencies at once (batch validation).

    Args:
        **kwargs: Dict mapping dependency name to (obj, interface, allow_none) tuple

    Example:
        >>> validate_dependencies(
        ...     task_repo=(task_repo, ITaskRepository, False),
        ...     logger=(logger, ILogger, False),
        ...     cache=(cache, ICache, True),  # Optional
        ... )
    """
    for name, (obj, interface, allow_none) in kwargs.items():
        validate_dependency(obj, interface, name, allow_none)
