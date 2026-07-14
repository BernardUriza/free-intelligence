"""Shared fixtures for the surviving suite (post-castigo 2026-07-14).

The insult-era Container/cog fixtures died with ``personas/``. What remains
fixtures the shared layer: the Postgres-backed ``pg_memory_store`` (used by the
khimeras_shared memory tests) and a generic mocked MemoryStore.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from khimeras_shared.style import UserStyleProfile

# Pull in the Postgres-backed fixture (`pg_memory_store`) plus its supporting
# pytest-postgresql factories. The module is import-safe even when pg_ctl is
# absent — the `REQUIRES_PG` marker handles skipping per-test in that case.
from tests._pg_fixture import PG_CTL, REQUIRES_PG  # noqa: F401

if PG_CTL is not None:  # pragma: no cover — environment-dependent branch
    from tests._pg_fixture import (  # noqa: F401  (factories registered by-name)
        pg_memory_store,
        postgresql_proc,
        postgresql_socket,
    )


@pytest.fixture
def mock_memory():
    """Mocked MemoryStore with async methods (khimeras_shared.memory surface)."""
    mem = AsyncMock()
    mem.store = AsyncMock()
    mem.get_recent = AsyncMock(return_value=[])
    mem.search = AsyncMock(return_value=[])
    mem.get_stats = AsyncMock(return_value={"total_messages": 0, "unique_users": 0, "unique_channels": 0})
    mem.get_profile = AsyncMock(return_value=UserStyleProfile())
    mem.update_profile = AsyncMock(return_value=UserStyleProfile())
    mem.build_context = MagicMock(return_value=[])
    mem.connect = AsyncMock()
    mem.close = AsyncMock()
    return mem
