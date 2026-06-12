"""Azure Blob Storage helpers.

Post-PG migration (2026-05-12): the DB no longer lives in blob storage —
Azure Database for PostgreSQL Flexible Server is the persistent data
plane. This module shrank to a single purpose: detect whether the
container is running in the Azure environment so dashboard exports and
the Siesta presence updater can short-circuit cleanly when we're on a
dev box without the connection string.

The previous bulk of this file — `download_db`, `upload_db`,
`count_authoritative_rows`, `should_unstick_baseline` — was deleted
because every one of them assumed SQLite-in-blob persistence. The race
they guarded against (mid-deploy blob restore) cannot happen anymore:
Postgres is external, container restarts touch zero rows.
"""

import os


def is_azure_configured() -> bool:
    """Whether `AZURE_STORAGE_CONNECTION_STRING` is set.

    Kept as a generic "running in our Azure deployment" detector — the
    dashboard exporter and the Siesta presence listener still use it to
    decide whether to touch blob storage at all. Both of those write
    artifacts that have nothing to do with the database.
    """
    return bool(os.environ.get("AZURE_STORAGE_CONNECTION_STRING"))
