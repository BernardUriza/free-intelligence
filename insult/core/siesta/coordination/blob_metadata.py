"""DEPRECATED v3.9.46 — kept only for tests and historical reference.

The Siesta coordination has moved to Postgres (`pg_state.py`). This module
is no longer imported by the runtime (`__init__.py` and `poller.py` both
import `pg_state` now). The blob metadata hijack is gone, which is what
finally unblocks deleting the `memory.db` blob entirely (POST-DEPLOY-1).

Why kept on disk:
- Existing tests in `tests/test_siesta_blob_metadata.py` exercise the
  pure parser (`parse_metadata`) and don't need Azure.
- Historical reference for the design rationale of the blob hijack.

DO NOT use the writer functions (`mark_*`) from this module — they will
silently no-op against the production data plane (writes go to Azure blob
metadata that nothing else reads). Use `pg_state` instead.

Original docstring kept below for context:

Cross-process coordination via Azure blob metadata.
The consolidator job and the bot replica are different processes — they
can't share memory or use Python locks. The shared object they BOTH
already touch is the `memory.db` blob in Azure Storage. Azure lets us
attach arbitrary string metadata to a blob; we hijack that channel.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import structlog

from insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot

log = structlog.get_logger()

CONTAINER_NAME = "insult-bot"
BLOB_NAME = "memory.db"

_KEY_PHASE = "siesta_phase"
_KEY_STARTED = "siesta_started_at"
_KEY_TOTAL = "siesta_total_users"
_KEY_PROCESSED = "siesta_processed_users"
_KEY_CURRENT = "siesta_current_user_id"


def _is_configured() -> bool:
    return bool(os.environ.get("AZURE_STORAGE_CONNECTION_STRING"))


def _build_metadata(snapshot: SiestaSnapshot) -> dict[str, str]:
    """Render a snapshot as Azure metadata strings (all values are str)."""
    metadata = {
        _KEY_PHASE: snapshot.phase.value,
        _KEY_TOTAL: str(snapshot.total_users),
        _KEY_PROCESSED: str(snapshot.processed_users),
    }
    if snapshot.started_at is not None:
        metadata[_KEY_STARTED] = snapshot.started_at.isoformat()
    if snapshot.current_user_id:
        metadata[_KEY_CURRENT] = snapshot.current_user_id
    return metadata


def parse_metadata(raw: dict[str, str] | None) -> SiestaSnapshot:
    """Inverse of ``_build_metadata`` — pure, no I/O. Tolerant of missing keys.

    Returns AWAKE on any parse failure or when the phase key is absent.
    Designed to be called in a hot path (every poll) so it must never
    raise on garbage metadata.
    """
    if not raw:
        return AWAKE
    phase_str = raw.get(_KEY_PHASE)
    if not phase_str:
        return AWAKE
    try:
        phase = SiestaPhase(phase_str)
    except ValueError:
        log.warning("siesta_metadata_invalid_phase", value=phase_str)
        return AWAKE
    if phase == SiestaPhase.AWAKE:
        return AWAKE

    started_at: datetime | None = None
    if started_str := raw.get(_KEY_STARTED):
        try:
            started_at = datetime.fromisoformat(started_str)
        except ValueError:
            log.warning("siesta_metadata_invalid_started", value=started_str)

    return SiestaSnapshot(
        phase=phase,
        started_at=started_at,
        total_users=_safe_int(raw.get(_KEY_TOTAL)),
        processed_users=_safe_int(raw.get(_KEY_PROCESSED)),
        current_user_id=raw.get(_KEY_CURRENT) or None,
    )


def _safe_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


async def _set_metadata(metadata: dict[str, str]) -> bool:
    """Merge metadata onto the blob without overwriting unrelated keys."""
    if not _is_configured():
        return False
    try:
        from azure.storage.blob.aio import BlobServiceClient

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            blob = client.get_blob_client(CONTAINER_NAME, BLOB_NAME)
            existing = (await blob.get_blob_properties()).metadata or {}
            existing.update(metadata)
            await blob.set_blob_metadata(existing)
            return True
    except ImportError:
        log.warning("azure_sdk_not_installed_for_siesta")
        return False
    except Exception:
        log.exception("siesta_metadata_write_failed")
        return False


async def mark_started(total_users: int, *, phase: SiestaPhase = SiestaPhase.LIGHT) -> bool:
    """Consolidator: announce the run is starting."""
    snapshot = SiestaSnapshot(
        phase=phase,
        started_at=datetime.now(UTC),
        total_users=total_users,
        processed_users=0,
    )
    return await _set_metadata(_build_metadata(snapshot))


async def mark_progress(
    *,
    phase: SiestaPhase,
    started_at: datetime,
    total_users: int,
    processed_users: int,
    current_user_id: str | None = None,
) -> bool:
    """Consolidator: announce phase or per-user advance."""
    snapshot = SiestaSnapshot(
        phase=phase,
        started_at=started_at,
        total_users=total_users,
        processed_users=processed_users,
        current_user_id=current_user_id,
    )
    return await _set_metadata(_build_metadata(snapshot))


async def mark_finished() -> bool:
    """Consolidator: clear the metadata so the bot wakes up.

    Always called in a ``finally`` so even crashes don't leave the bot
    in a stuck siesta. Sets ``phase=awake`` and zeroes the counters.
    """
    return await _set_metadata(_build_metadata(AWAKE))


async def read_snapshot() -> SiestaSnapshot:
    """Bot poller: fetch and parse the current state. Never raises."""
    if not _is_configured():
        return AWAKE
    try:
        from azure.storage.blob.aio import BlobServiceClient

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            blob = client.get_blob_client(CONTAINER_NAME, BLOB_NAME)
            props = await blob.get_blob_properties()
            return parse_metadata(props.metadata)
    except ImportError:
        return AWAKE
    except Exception:
        log.exception("siesta_metadata_read_failed")
        return AWAKE
