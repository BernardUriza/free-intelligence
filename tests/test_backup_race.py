"""Unit tests for the shutdown-upload race policy.

Post-PG migration (2026-05-12): the entire blob-as-DB-storage architecture
is gone. Postgres is the persistent data plane; container restarts no
longer touch user data. The functions this file tested
(``should_abort_upload``, ``count_authoritative_rows``,
``should_unstick_baseline``, etc.) were deleted along with the SQLite
blob-restore loop. The whole module is skipped so the suite stays green
while we keep the file as a historical marker until the next prune pass.

Original failure mode this used to lock in (2026-04-21 05:05 UTC): a
dying container's shutdown hook overwrote the blob with a stale in-memory
DB, losing 13 manual facts. The Postgres migration makes that scenario
impossible at the architecture level — no compute-plane container can
mutate the DB by virtue of being alive or dying.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="post-PG migration: blob-backup race functions removed; nothing to test")
