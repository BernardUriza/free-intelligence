"""Checkpoint Use Cases - Application Business Logic.

Use cases orchestrate domain objects and ports to fulfill business requirements.
They contain the application-specific business rules.

Clean Architecture: Use cases are the application layer.
They depend on domain and ports, but not on adapters.
"""

from .checkpoint_use_case import CheckpointUseCase

__all__ = [
    "CheckpointUseCase",
]
