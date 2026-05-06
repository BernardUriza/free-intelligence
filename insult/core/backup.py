"""Azure Blob Storage backup for SQLite database.

Optional: only activates if AZURE_STORAGE_CONNECTION_STRING is set.
Downloads DB on startup, uploads on shutdown + periodic backup.

Race-condition handling: `download_db` tracks the blob's last_modified
timestamp in a module-level _last_known_blob_mtime. `upload_db` checks
before writing — if the remote blob is newer than what we last saw,
we abort instead of overwriting. This stops the shutdown hook of a
dying container from clobbering the new container's already-uploaded
version during a restart.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import structlog

log = structlog.get_logger()

CONTAINER_NAME = "insult-bot"
BLOB_NAME = "memory.db"

# Tracks the blob's last_modified as of our most recent read. Periodic upload
# refreshes this after a successful write; shutdown compares against it.
_last_known_blob_mtime: datetime | None = None

# Tracks the remote mtime observed during the previous upload attempt that was
# aborted because the remote looked newer. If the next attempt sees the same
# mtime, the writer that "won" the race is gone (the blob has been stable for
# at least one interval) and we can safely adopt their mtime as our baseline.
# Without this, a single write by a dying replacement permanently freezes
# uploads from this container until restart.
_last_observed_remote_mtime: datetime | None = None


def is_azure_configured() -> bool:
    """Check if Azure Blob Storage credentials are available."""
    return bool(os.environ.get("AZURE_STORAGE_CONNECTION_STRING"))


def should_unstick_baseline(
    current_remote_mtime: datetime | None,
    last_observed_remote_mtime: datetime | None,
) -> bool:
    """Whether to adopt the current remote mtime as our new baseline.

    Pure function so the recovery policy can be unit-tested without the SDK.
    Returns True only when the blob's last_modified is identical to what we
    observed during the previous aborted upload — i.e. it has been stable
    for at least one full backup interval, so any competing writer is gone.

    A single observation is not enough: on the very first abort we have no
    prior observation, so we must wait one more cycle before unsticking.
    """
    if current_remote_mtime is None or last_observed_remote_mtime is None:
        return False
    return current_remote_mtime == last_observed_remote_mtime


def count_authoritative_rows(db_path: Path) -> dict[str, int]:
    """Return row counts for the tables that hold longitudinal user data.

    Pure on inputs (just opens the file read-only) so it can be unit-tested
    against synthetic SQLite files without azure-storage-blob installed.
    Returns 0 for any table that is missing — a brand-new container's
    freshly initialized DB might be missing rarely-used tables in transit,
    and a missing table is informationally equivalent to "no rows" for the
    purpose of the richness comparison.

    Tables counted: `messages` (append-only conversation memory) and
    `user_facts` (extracted facts that drive the vulnerability overlay).
    These are the load-bearing tables — losing them is the failure mode
    we are guarding against. We deliberately ignore derived tables
    (summaries, consolidation_log, scans) because they can be regenerated.
    """
    import sqlite3

    counts = {"messages": 0, "user_facts": 0}
    if not db_path.exists():
        return counts
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            for table in counts:
                try:
                    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 — table names are constants above
                    row = cur.fetchone()
                    counts[table] = int(row[0]) if row else 0
                except sqlite3.OperationalError:
                    counts[table] = 0
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return counts
    return counts


def should_force_overwrite(
    local_counts: dict[str, int],
    remote_counts: dict[str, int],
) -> bool:
    """Whether a richer local DB justifies overwriting a strictly-newer remote.

    Pure function. Returns True only when the local DB is comprehensively
    richer than the remote — i.e. local has at least one of {messages,
    user_facts} with strictly more rows, AND no authoritative table where
    local has fewer rows than remote. This second clause is the safety
    valve: if remote has facts we don't have, an operator (or another
    writer) added them; we should NOT clobber.

    Distinguishes the two contradictory race scenarios:
    - Operator-pushed fresh blob (2026-04-21): local has 3 facts, remote
      has 16 facts → local NOT richer → abort (existing behaviour).
    - Long-running rich container (2026-04-27): local has 92 facts, remote
      has 4 facts → local strictly richer → force overwrite (new path).
    """
    has_strict_gain = False
    for table in ("messages", "user_facts"):
        local = int(local_counts.get(table, 0))
        remote = int(remote_counts.get(table, 0))
        if local < remote:
            return False
        if local > remote:
            has_strict_gain = True
    return has_strict_gain


def should_abort_download(
    local_counts: dict[str, int],
    remote_counts: dict[str, int],
) -> bool:
    """Whether the download must be aborted because the remote blob is
    strictly poorer than the local DB.

    Pure function — symmetric to `should_force_overwrite` on the upload
    path. Returns True only when, for every authoritative table, local has
    >= remote rows AND for at least one table local has STRICTLY MORE rows.
    In that case, downloading would erase rows we have on disk that the
    remote does not — exactly the regression that wiped Alex's clinical
    fact cluster (CPTSD, quetiapina, sertralina, neuropsiquiatra, artritis)
    on 2026-04-27 when a fresh container restored a stale blob over a
    long-running rich replica.

    The startup path calls this AFTER fetching the remote bytes into a
    side-buffer but BEFORE atomically replacing the local DB file. Pure
    function so the policy can be unit-tested without azure-storage-blob.

    Note: this is intentionally aggressive. If you ever need to manually
    restore a blob that has fewer rows on purpose (e.g. operator bisecting
    bad facts), bypass it by clearing storage/memory.db before the
    container starts so `local_counts` is all zeros — `proceed`.
    """
    has_strict_gain = False
    for table in ("messages", "user_facts"):
        local = int(local_counts.get(table, 0))
        remote = int(remote_counts.get(table, 0))
        if local < remote:
            return False
        if local > remote:
            has_strict_gain = True
    return has_strict_gain


def should_abort_upload(
    current_remote_mtime: datetime | None,
    last_known_local_mtime: datetime | None,
    *,
    skip_if_remote_newer: bool = True,
) -> bool:
    """Decide whether to skip an upload because the remote blob is newer.

    Pure function — no SDK, no I/O — so the shutdown-race policy can be
    unit-tested without azure-storage-blob installed locally. Returns True
    when the caller MUST abort the upload (remote has been modified by
    another writer after our last download/upload).

    Rules:
    - If skip_if_remote_newer is False, never abort.
    - If we have no last-known mtime, proceed (first-ever upload / race-free).
    - If we can't determine the remote mtime, proceed (fail-open — better a
      stale overwrite than no backup).
    - Otherwise, abort iff the remote mtime is STRICTLY newer than what we
      last observed.
    """
    if not skip_if_remote_newer:
        return False
    if last_known_local_mtime is None:
        return False
    if current_remote_mtime is None:
        return False
    return current_remote_mtime > last_known_local_mtime


async def download_db(db_path: Path) -> bool:
    """Download memory.db from Azure Blob Storage if it exists.

    Records the blob's last_modified so upload_db can detect if the blob
    has been modified by someone else (new container, manual operator)
    before overwriting it.

    Returns True if downloaded, False if not found or not configured.
    """
    global _last_known_blob_mtime

    if not is_azure_configured():
        return False

    try:
        from azure.storage.blob.aio import BlobServiceClient

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            container = client.get_container_client(CONTAINER_NAME)

            # Create container if it doesn't exist
            try:
                await container.create_container()
                log.info("azure_container_created", container=CONTAINER_NAME)
            except Exception:  # noqa: S110 — expected when container already exists
                pass

            blob = container.get_blob_client(BLOB_NAME)
            try:
                stream = await blob.download_blob()
                data = await stream.readall()
                props = await blob.get_blob_properties()
                _last_known_blob_mtime = props.last_modified

                # Don't overwrite a local DB that already has data with an empty/smaller blob
                if db_path.exists() and db_path.stat().st_size > len(data):
                    log.warning(
                        "azure_download_skipped_larger_local",
                        local_size=db_path.stat().st_size,
                        blob_size=len(data),
                    )
                    return False

                # Richness guard: if the local DB exists and is strictly
                # richer than the remote (more messages or user_facts and
                # never fewer of either), refuse to overwrite. This is the
                # symmetric counterpart of `should_force_overwrite` on the
                # upload path. It guards against the regression discovered
                # 2026-04-27 where a container swap pulled a stale 4-fact
                # blob over a 92-fact local DB. Byte-size alone (the older
                # check above) is insufficient: a VACUUMed rich DB can be
                # smaller than a bloated stale one.
                db_path.parent.mkdir(parents=True, exist_ok=True)
                if db_path.exists():
                    remote_check_path = db_path.parent / "memory_remote_check.db"
                    try:
                        remote_check_path.write_bytes(data)
                        local_counts = count_authoritative_rows(db_path)
                        remote_counts = count_authoritative_rows(remote_check_path)
                        if should_abort_download(local_counts, remote_counts):
                            log.warning(
                                "azure_download_aborted_richer_local",
                                local_counts=local_counts,
                                remote_counts=remote_counts,
                                reason="local DB is strictly richer; downloading would erase rows",
                            )
                            return False
                    finally:
                        remote_check_path.unlink(missing_ok=True)

                db_path.write_bytes(data)
                log.info(
                    "azure_db_downloaded",
                    size=len(data),
                    path=str(db_path),
                    blob_mtime=props.last_modified.isoformat() if props.last_modified else None,
                )
                return True
            except Exception:
                log.info("azure_db_not_found", blob=BLOB_NAME)
                return False

    except ImportError:
        log.warning("azure_sdk_not_installed", hint="pip install azure-storage-blob")
        return False
    except Exception:
        log.exception("azure_download_failed")
        return False


async def upload_db(db_path: Path, *, skip_if_remote_newer: bool = True) -> bool:
    """Upload memory.db to Azure Blob Storage.

    Creates a consistent snapshot via SQLite backup API (safe even with WAL mode),
    then uploads the snapshot. This avoids issues with WAL journal not being flushed.

    If `skip_if_remote_newer` is True and the remote blob has a last_modified
    timestamp after our last known one (i.e. someone else — typically the new
    container that just arrived during a restart — wrote to it), we skip the
    upload and log the reason. This prevents the shutdown race where the dying
    container overwrites the fresh upload.

    Returns True if uploaded, False if not configured, failed, or skipped.
    """
    global _last_known_blob_mtime, _last_observed_remote_mtime

    if not is_azure_configured():
        return False

    if not db_path.exists():
        log.warning("azure_upload_skipped", reason="db file does not exist")
        return False

    try:
        import sqlite3

        from azure.storage.blob.aio import BlobServiceClient

        # Create a consistent snapshot using SQLite backup API
        # This merges WAL into a single file — safe while DB is open
        snapshot_path = db_path.parent / "memory_backup.db"
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(snapshot_path))
        src.backup(dst)
        src.close()
        dst.close()

        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        async with BlobServiceClient.from_connection_string(conn_str) as client:
            container = client.get_container_client(CONTAINER_NAME)
            blob = container.get_blob_client(BLOB_NAME)

            # Freshness check: has the remote changed since we last saw it?
            if skip_if_remote_newer and _last_known_blob_mtime is not None:
                current_mtime: datetime | None = None
                try:
                    current_props = await blob.get_blob_properties()
                    current_mtime = current_props.last_modified
                except Exception:
                    # Fail-open: better a stale overwrite than no backup.
                    log.warning("azure_upload_freshness_check_failed_proceeding")
                if should_abort_upload(
                    current_mtime,
                    _last_known_blob_mtime,
                    skip_if_remote_newer=True,
                ):
                    # Before aborting, check if the local snapshot is richer
                    # than the remote. Distinguishes operator-pushed-fresh
                    # (local stale → abort) from long-running-rich-container
                    # (local rich → force overwrite). See should_force_overwrite
                    # for the policy.
                    remote_check_path = db_path.parent / "memory_remote_check.db"
                    forced = False
                    try:
                        try:
                            stream = await blob.download_blob()
                            remote_bytes = await stream.readall()
                            remote_check_path.write_bytes(remote_bytes)
                            local_counts = count_authoritative_rows(snapshot_path)
                            remote_counts = count_authoritative_rows(remote_check_path)
                            if should_force_overwrite(local_counts, remote_counts):
                                log.warning(
                                    "azure_upload_force_overwrite_richer_local",
                                    last_known=_last_known_blob_mtime.isoformat(),
                                    current=current_mtime.isoformat() if current_mtime else None,
                                    local_counts=local_counts,
                                    remote_counts=remote_counts,
                                    reason="local DB is comprehensively richer; remote-newer abort would lose data",
                                )
                                _last_observed_remote_mtime = None
                                forced = True
                        except Exception:
                            log.exception("azure_upload_richness_check_failed")
                    finally:
                        remote_check_path.unlink(missing_ok=True)

                    if not forced:
                        if current_mtime is not None and should_unstick_baseline(
                            current_mtime, _last_observed_remote_mtime
                        ):
                            log.info(
                                "azure_upload_freshness_unstuck",
                                last_known=_last_known_blob_mtime.isoformat(),
                                stable_remote=current_mtime.isoformat(),
                                reason="remote unchanged across two consecutive checks — race window over",
                            )
                            _last_known_blob_mtime = current_mtime
                            _last_observed_remote_mtime = None
                        else:
                            _last_observed_remote_mtime = current_mtime
                            log.warning(
                                "azure_upload_aborted_remote_newer",
                                last_known=_last_known_blob_mtime.isoformat(),
                                current=current_mtime.isoformat() if current_mtime else None,
                                reason="remote was updated by another writer (likely the replacement container)",
                            )
                            snapshot_path.unlink(missing_ok=True)
                            return False
                else:
                    # Remote is at-or-behind our baseline; no race signal pending.
                    _last_observed_remote_mtime = None

            data = snapshot_path.read_bytes()
            resp = await blob.upload_blob(data, overwrite=True)
            # Refresh our tracked mtime so later uploads from this same
            # process compare against our own write, not a stale download.
            _last_known_blob_mtime = resp.get("last_modified") or datetime.now(UTC)
            log.info("azure_db_uploaded", size=len(data), blob=BLOB_NAME)

            # Cleanup snapshot
            snapshot_path.unlink(missing_ok=True)
            return True

    except ImportError:
        log.warning("azure_sdk_not_installed", hint="pip install azure-storage-blob")
        return False
    except Exception:
        log.exception("azure_upload_failed")
        return False
