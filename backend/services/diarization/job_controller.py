"""DiarizationJobService - Reads job state from HDF5 and resolves inconsistencies.

Supports both scalar Dataset (JSON serialized) and Group structures.
Resolves inconsistent states (e.g., completed with soap_status=failed) to completed_with_errors.

Compatible with Python 3.9.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import h5py

from backend.logger import get_logger

logger = get_logger(__name__)


def now_utc() -> datetime:
    """Python 3.9 compatible timezone.utc now."""
    return datetime.now(timezone.utc)


@dataclass
class DiarizationJobRecord:
    """Internal job record representation."""

    job_id: str
    session_id: str
    status: str
    progress_percent: int
    created_at: str
    completed_at: Optional[str]
    result_data: Dict[str, Any]


class DiarizationJobService:
    """Reads jobs from HDF5 (scalar Dataset or Group) and resolves coherent state.

    If `persist_resolved=True` and source is scalar Dataset, can rewrite JSON with resolved status.
    """

    def __init__(self, hdf5_path: str, persist_resolved: bool = False) -> None:
        """Initialize service.

        Args:
            hdf5_path: Path to diarization.h5 file
            persist_resolved: Whether to persist resolved status back to HDF5
        """
        self.hdf5_path = hdf5_path
        self.persist_resolved = persist_resolved
        logger.info(
            "DiarizationJobService initialized",
            hdf5_path=hdf5_path,
            persist_resolved=persist_resolved,
        )

    # Public API ------------------------------------------------------------

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status with resolved state.

        Args:
            job_id: Job UUID

        Returns:
            Dict with job status, resolved_status, and errors if any

        Raises:
            FileNotFoundError: If HDF5 file doesn't exist
            KeyError: If job not found
        """
        record, source = self._load_job(job_id)
        resolved_status, errors = self._resolve_status(record)

        response: Dict[str, Any] = {
            **record.__dict__,
            "resolved_status": resolved_status,
        }
        if errors:
            response["errors"] = errors

        # For backwards compatibility with current FE, return resolved status
        response["status"] = resolved_status

        # Ensure progress 100 in completed_with_errors
        if resolved_status == "completed_with_errors" and response.get("progress_percent", 0) < 100:
            response["progress_percent"] = 100

        # Persist optional only if source is scalar Dataset (simple rewrite)
        # Note: must happen AFTER status and progress_percent are updated
        if self.persist_resolved and source == "dataset":
            self._persist_scalar(job_id, response)

        logger.info(
            "JOB_STATUS_RETRIEVED",
            job_id=job_id,
            original_status=record.status,
            resolved_status=resolved_status,
            errors_count=len(errors),
        )

        return response

    def get_job_logs(self, job_id: str) -> list[Dict[str, Any]]:
        """Get audit logs for a diarization job.

        Args:
            job_id: Job UUID

        Returns:
            List of log entries sorted by timestamp (newest first)

        Raises:
            FileNotFoundError: If corpus.h5 file doesn't exist
            KeyError: If job not found in diarization.h5
        """
        # First verify the job exists
        try:
            self._load_job(job_id)
        except (FileNotFoundError, KeyError) as e:
            logger.error("JOB_NOT_FOUND_FOR_LOGS", job_id=job_id, error=str(e))
            raise

        # Retrieve audit logs from corpus.h5
        corpus_path = pathlib.Path(self.hdf5_path).parent / "corpus.h5"
        if not corpus_path.exists():
            logger.warning("CORPUS_H5_NOT_FOUND", path=str(corpus_path))
            return []

        logs = []
        with h5py.File(corpus_path.as_posix(), "r") as f:
            if "audit_logs" not in f:
                logger.warning("NO_AUDIT_LOGS_GROUP", path=str(corpus_path))
                return []

            audit_logs = f["audit_logs"]
            for log_id in audit_logs.keys():
                log_group = audit_logs[log_id]
                resource = log_group.attrs.get("resource", "")

                # Filter logs related to this job
                if job_id in str(resource):
                    log_entry = {
                        "log_id": log_id,
                        "timestamp": log_group.attrs.get("timestamp", ""),
                        "action": log_group.attrs.get("action", ""),
                        "user_id": log_group.attrs.get("user_id", ""),
                        "resource": resource,
                        "result": log_group.attrs.get("result", ""),
                    }

                    # Parse details if available
                    details_str = log_group.attrs.get("details", "")
                    if details_str:
                        try:
                            log_entry["details"] = json.loads(details_str)
                        except json.JSONDecodeError:
                            log_entry["details"] = details_str

                    logs.append(log_entry)

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        logger.info("JOB_LOGS_RETRIEVED", job_id=job_id, log_count=len(logs))
        return logs

    # Loading ---------------------------------------------------------------

    def _load_job(self, job_id: str) -> Tuple[DiarizationJobRecord, str]:
        """Load job from HDF5.

        Args:
            job_id: Job UUID

        Returns:
            Tuple of (DiarizationJobRecord, source_type)
            source_type is either "dataset" or "group"

        Raises:
            FileNotFoundError: If HDF5 file doesn't exist
            KeyError: If job not found
            TypeError: If node type is unsupported
        """
        p = pathlib.Path(self.hdf5_path)
        if not p.exists():
            raise FileNotFoundError(f"HDF5 not found: {p}")

        with h5py.File(p.as_posix(), "r") as f:
            node = f.get(f"/jobs/{job_id}")
            if node is None:
                raise KeyError(f"job {job_id} not found")

            # Scalar Dataset with JSON serialized
            if isinstance(node, h5py.Dataset) and node.shape == ():
                raw = node[()]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                data = json.loads(raw)
                logger.debug("JOB_LOADED_FROM_DATASET", job_id=job_id)
                return self._to_record(data), "dataset"

            # Group with sub-datasets (flexible)
            if isinstance(node, h5py.Group):
                data: Dict[str, Any] = {}

                # Common strategies: "payload"/"meta" datasets or JSON attributes
                if "payload" in node:
                    val = node["payload"][()]
                    if isinstance(val, bytes):
                        val = val.decode("utf-8")
                    data.update(json.loads(val))

                if "meta" in node:
                    val = node["meta"][()]
                    if isinstance(val, bytes):
                        val = val.decode("utf-8")
                    data.update(json.loads(val))

                # Optional attributes
                for k, v in node.attrs.items():
                    try:
                        if isinstance(v, (bytes, bytearray)):
                            v = v.decode("utf-8")
                        if isinstance(v, str) and v and v[0] in "[{":
                            data[k] = json.loads(v)
                        else:
                            data[k] = v
                    except Exception:
                        data[k] = str(v)

                logger.debug("JOB_LOADED_FROM_GROUP", job_id=job_id)
                return self._to_record(data), "group"

            raise TypeError("Unsupported HDF5 node type for diarization job")

    def _to_record(self, data: Dict[str, Any]) -> DiarizationJobRecord:
        """Convert raw dict to DiarizationJobRecord.

        Args:
            data: Raw job data from HDF5

        Returns:
            DiarizationJobRecord instance
        """
        return DiarizationJobRecord(
            job_id=data.get("job_id", ""),
            session_id=data.get("session_id", ""),
            status=str(data.get("status", "unknown")),
            progress_percent=int(data.get("progress_percent", 0)),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            result_data=data.get("result_data", {}),
        )

    # State resolution ------------------------------------------------------

    def _resolve_status(self, record: DiarizationJobRecord) -> Tuple[str, list]:
        """Resolve job status to coherent state.

        Checks for inconsistencies like:
        - status="completed" but soap_status="failed" → "completed_with_errors"

        Args:
            record: DiarizationJobRecord to resolve

        Returns:
            Tuple of (resolved_status, errors_list)
        """
        errors = []
        soap_status = None
        soap_error = None

        if isinstance(record.result_data, dict):
            soap_status = record.result_data.get("soap_status")
            soap_error = record.result_data.get("soap_error")

        status = record.status

        # Normalize completed states
        if status in {"completed", "succeeded", "done"}:
            if soap_status == "failed" or soap_error:
                status = "completed_with_errors"
                if soap_error:
                    errors.append({"component": "soap", "message": str(soap_error)})
                logger.info(
                    "STATUS_RESOLVED_TO_COMPLETED_WITH_ERRORS",
                    job_id=record.job_id,
                    soap_error=soap_error,
                )

        elif status in {"failed", "error"}:
            status = "failed"

        elif status in {"running", "in_progress", "pending"}:
            # No changes for in-progress states
            pass

        else:
            # Basic normalization
            status = str(status).lower()

        return status, errors

    # Optional persistence --------------------------------------------------

    def _persist_scalar(self, job_id: str, response: Dict[str, Any]) -> None:
        """Rewrite scalar Dataset with resolved status (idempotent).

        Args:
            job_id: Job UUID
            response: Response dict with resolved status
        """
        data_str = json.dumps(
            {
                "job_id": response.get("job_id"),
                "session_id": response.get("session_id", ""),
                "status": response.get("status"),
                "progress_percent": response.get("progress_percent", 0),
                "created_at": response.get("created_at"),
                "completed_at": response.get("completed_at"),
                "result_data": response.get("result_data", {}),
            },
            ensure_ascii=False,
        )

        with h5py.File(self.hdf5_path, "a") as f:
            path = f"/jobs/{job_id}"
            if path in f:
                del f[path]
            # Use string_dtype to avoid object dtype issues
            f.create_dataset(path, data=data_str, dtype=h5py.string_dtype(encoding="utf-8"))

        logger.info("JOB_STATUS_PERSISTED", job_id=job_id, status=response.get("status"))
