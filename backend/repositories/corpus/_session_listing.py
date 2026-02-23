"""Session-listing operations for the corpus HDF5 store.

Provides ``list_all_sessions`` (simple listing) and
``list_all_sessions_with_metadata`` (paginated, multi-tenant,
detail-rich listing used by the sessions-list API).

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

from typing import Any

import h5py
from backend.utils.common.logging.logger import get_logger

from ._extractors import (
    extract_doctor_name_from_diarization,
    extract_session_created_at,
    extract_transcription_details,
)
from ._session_reader import SESSIONS_GROUP

logger = get_logger(__name__)


class SessionListing:
    """Session enumeration and paginated listing.

    The heavy ``list_all_sessions_with_metadata`` method is split into
    two clear phases:

    1. **Collect** — gather session IDs with timestamps, apply
       multi-tenancy filter, sort by newest first, paginate.
    2. **Enrich** — build detail dicts (task flags, durations,
       doctor / patient names) for the current page only.
    """

    def __init__(
        self,
        open_file: Any,
        log_operation: Any,
        h5_file_path: Any,
        get_session_metadata: Any,
    ) -> None:
        """Initialise with shared helpers.

        Args:
            open_file: Context-manager factory for HDF5 access.
            log_operation: Audit-trail callable.
            h5_file_path: Direct path to the HDF5 file (used by the
                paginated listing which opens the file independently).
            get_session_metadata: Bound method from ``SessionReader``
                for the simple listing path.
        """
        self._open_file = open_file
        self._log_operation = log_operation
        self._h5_file_path = h5_file_path
        self._get_session_metadata = get_session_metadata

    # -- simple listing ------------------------------------------------------

    def list_all_sessions(
        self,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """Return sessions with metadata (simple, non-paginated).

        Args:
            limit: Cap on returned sessions.
            include_deleted: Include soft-deleted sessions.
        """
        try:
            with self._open_file("r") as f:
                if SESSIONS_GROUP not in f:
                    return []

                sessions_group = f[SESSIONS_GROUP]
                session_ids = list(sessions_group.keys())

                if limit:
                    session_ids = session_ids[:limit]

                results: list[dict[str, Any]] = []
                for session_id in session_ids:
                    session_meta = self._get_session_metadata(session_id)
                    if session_meta:
                        is_deleted = session_meta.get("deleted_at") is not None
                        if include_deleted or not is_deleted:
                            results.append(
                                {"session_id": session_id, "metadata": session_meta}
                            )

                logger.debug("SESSIONS_LIST_READ", count=len(results))
                return results

        except Exception as e:
            logger.error("LIST_SESSIONS_FAILED", error=str(e))
            return []

    # -- paginated / multi-tenant listing ------------------------------------

    def list_all_sessions_with_metadata(
        self,
        limit: int = 20,
        offset: int = 0,
        clinic_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List sessions with full detail (paginated, multi-tenant).

        Multi-Tenancy:
            * ``clinic_id`` provided → only sessions from that clinic.
            * ``clinic_id is None`` → all sessions (SUPERADMIN mode).

        Returns:
            ``(sessions_page, total_count)``
        """
        try:
            with h5py.File(self._h5_file_path, "r") as f:
                if SESSIONS_GROUP not in f:
                    logger.warning("NO_SESSIONS_GROUP_IN_HDF5")
                    return ([], 0)

                sessions_group = f[SESSIONS_GROUP]

                # Phase 1 — collect + filter + sort + paginate
                collected = _collect_session_ids(sessions_group, clinic_id)
                collected.sort(key=lambda x: x[1], reverse=True)
                total_count = len(collected)
                page = collected[offset : offset + limit]

                # Phase 2 — enrich current page only
                sessions_list = _enrich_sessions(sessions_group, page)

            logger.info(
                "SESSIONS_LIST_SUCCESS",
                total=total_count,
                returned=len(sessions_list),
                clinic_id_filter=clinic_id,
            )
            return (sessions_list, total_count)

        except Exception as e:
            logger.error("LIST_ALL_SESSIONS_FAILED", error=str(e), exc_info=True)
            return ([], 0)


# ---------------------------------------------------------------------------
# Private helpers (module-level, stateless)
# ---------------------------------------------------------------------------


def _collect_session_ids(
    sessions_group: Any,
    clinic_id: str | None,
) -> list[tuple[str, str]]:
    """Phase 1: gather ``(session_id, created_at)`` tuples.

    Applies the multi-tenancy ``clinic_id`` filter when provided.
    """
    results: list[tuple[str, str]] = []

    for session_id in sessions_group.keys():
        try:
            session_group = sessions_group[session_id]
            if "tasks" not in session_group:
                continue

            # Multi-tenancy filter
            if clinic_id is not None:
                session_clinic = (
                    session_group.attrs.get("clinic_id")
                    if hasattr(session_group, "attrs")
                    else None
                )
                if session_clinic != clinic_id:
                    continue

            created_at = extract_session_created_at(session_group["tasks"])
            results.append((session_id, created_at))

        except Exception as e:
            logger.warning(
                "SKIP_SESSION_METADATA", session_id=session_id, error=str(e)
            )

    return results


def _enrich_sessions(
    sessions_group: Any,
    page: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Phase 2: build detail dicts for the paginated slice."""
    sessions_list: list[dict[str, Any]] = []

    for session_id, created_at in page:
        try:
            session_group = sessions_group[session_id]
            if "tasks" not in session_group:
                continue

            tasks = session_group["tasks"]

            has_transcription = "TRANSCRIPTION" in tasks
            has_diarization = "DIARIZATION" in tasks
            has_soap = "SOAP_GENERATION" in tasks

            chunk_count, duration_seconds, preview = extract_transcription_details(
                tasks, session_id
            )

            patient_name = _safe_attr(session_group, "patient_name", "Paciente")
            doctor_name = _safe_attr(session_group, "doctor_name", "")

            if has_diarization and (patient_name == "Paciente" or not doctor_name):
                extracted = extract_doctor_name_from_diarization(tasks, session_id)
                if extracted:
                    doctor_name = extracted

            sessions_list.append(
                {
                    "session_id": session_id,
                    "created_at": created_at,
                    "has_transcription": has_transcription,
                    "has_diarization": has_diarization,
                    "has_soap": has_soap,
                    "chunk_count": chunk_count,
                    "duration_seconds": duration_seconds,
                    "preview": preview,
                    "patient_name": patient_name,
                    "doctor_name": doctor_name,
                }
            )

        except Exception as e:
            logger.warning(
                "SKIP_SESSION_DETAILS", session_id=session_id, error=str(e)
            )

    return sessions_list


def _safe_attr(group: Any, key: str, default: str) -> str:
    """Read an HDF5 group attribute with a safe fallback."""
    if hasattr(group, "attrs"):
        return str(group.attrs.get(key, default))
    return default
