"""Backend container module.

Provides access to the dependency injection container.
"""

from __future__ import annotations

from backend.utils.common.infrastructure.container import Container


def get_container() -> Container:
    """Get the application dependency injection container."""
    return Container()
