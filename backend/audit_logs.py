#!/usr/bin/env python3
"""
Free Intelligence - Audit Logs

Append-only audit trail for all critical operations.
Logs user, operation, timestamp, payload hash, and result hash.

FI-SEC-FEAT-003
"""

import h5py
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
from zoneinfo import ZoneInfo


# Audit log schema
AUDIT_LOG_SCHEMA = {
    "audit_id": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=36),
        "description": "UUID v4 for audit entry"
    },
    "timestamp": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=50),
        "description": "ISO 8601 timestamp with timezone"
    },
    "operation": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=100),
        "description": "Operation name (e.g., INTERACTION_APPENDED)"
    },
    "user_id": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=100),
        "description": "User identifier (owner_hash prefix or session_id)"
    },
    "endpoint": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=200),
        "description": "API endpoint or function name"
    },
    "payload_hash": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=64),
        "description": "SHA256 hash of input payload"
    },
    "result_hash": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=64),
        "description": "SHA256 hash of operation result"
    },
    "status": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=20),
        "description": "SUCCESS, FAILED, BLOCKED"
    },
    "metadata": {
        "dtype": h5py.string_dtype(encoding='utf-8', length=500),
        "description": "JSON metadata (optional)"
    }
}


def init_audit_logs_group(corpus_path: str) -> bool:
    """
    Initialize /audit_logs/ group in existing corpus.

    Args:
        corpus_path: Path to corpus.h5

    Returns:
        True if successful

    Examples:
        >>> init_audit_logs_group("storage/corpus.h5")
        True
    """
    from backend.logger import get_logger

    logger = get_logger()

    try:
        with h5py.File(corpus_path, 'a') as f:
            # Create audit_logs group if not exists
            if "audit_logs" in f:
                logger.info("AUDIT_LOGS_GROUP_EXISTS", path=corpus_path)
                return True

            audit_logs = f.create_group("audit_logs")

            # Create datasets
            for dataset_name, spec in AUDIT_LOG_SCHEMA.items():
                audit_logs.create_dataset(
                    dataset_name,
                    shape=(0,),
                    maxshape=(None,),
                    dtype=spec["dtype"],
                    chunks=True,
                    compression="gzip",
                    compression_opts=4
                )

            logger.info(
                "AUDIT_LOGS_GROUP_INITIALIZED",
                path=corpus_path,
                datasets=list(AUDIT_LOG_SCHEMA.keys())
            )

            return True

    except (IOError, OSError, ValueError, RuntimeError) as e:
        logger.error("AUDIT_LOGS_INIT_FAILED", error=str(e), path=corpus_path)
        return False


def hash_payload(payload: Any) -> str:
    """
    Generate SHA256 hash of payload.

    Args:
        payload: Any JSON-serializable data

    Returns:
        SHA256 hex digest

    Examples:
        >>> hash_payload({"user": "bernard", "action": "append"})
        'a3c5...'
    """
    # Convert to JSON string for consistent hashing
    if isinstance(payload, (dict, list)):
        payload_str = json.dumps(payload, sort_keys=True)
    else:
        payload_str = str(payload)

    return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()


def append_audit_log(
    corpus_path: str,
    operation: str,
    user_id: str,
    endpoint: str,
    payload: Optional[any] = None,
    result: Optional[any] = None,
    status: str = "SUCCESS",
    metadata: Optional[Dict] = None
) -> str:
    """
    Append audit log entry.

    Args:
        corpus_path: Path to corpus
        operation: Operation name (event name)
        user_id: User identifier
        endpoint: API endpoint or function name
        payload: Input payload (will be hashed)
        result: Operation result (will be hashed)
        status: SUCCESS, FAILED, BLOCKED
        metadata: Optional metadata dict

    Returns:
        audit_id (UUID v4)

    Examples:
        >>> audit_id = append_audit_log(
        ...     "storage/corpus.h5",
        ...     "INTERACTION_APPENDED",
        ...     "user_123",
        ...     "append_interaction",
        ...     payload={"prompt": "test"},
        ...     result={"interaction_id": "abc-123"}
        ... )
    """
    from backend.logger import get_logger
    from backend.append_only_policy import AppendOnlyPolicy
    import uuid

    logger = get_logger()
    audit_id = str(uuid.uuid4())

    # Generate timestamp
    tz = ZoneInfo("America/Mexico_City")
    timestamp = datetime.now(tz).isoformat()

    # Hash payload and result
    payload_hash = hash_payload(payload) if payload is not None else "NONE"
    result_hash = hash_payload(result) if result is not None else "NONE"

    # Serialize metadata
    metadata_str = json.dumps(metadata) if metadata else "{}"

    try:
        with AppendOnlyPolicy(corpus_path), h5py.File(corpus_path, 'a') as f:
            # Ensure audit_logs group exists
            if "audit_logs" not in f:
                init_audit_logs_group(corpus_path)
                # Reopen file
                f.close()
                f = h5py.File(corpus_path, 'a')

            audit_logs = f["audit_logs"]

            # Current size
            current_size = audit_logs["audit_id"].shape[0]
            new_size = current_size + 1

            # Resize all datasets
            for dataset_name in AUDIT_LOG_SCHEMA.keys():
                audit_logs[dataset_name].resize((new_size,))

            # Append data
            audit_logs["audit_id"][current_size] = audit_id
            audit_logs["timestamp"][current_size] = timestamp
            audit_logs["operation"][current_size] = operation
            audit_logs["user_id"][current_size] = user_id
            audit_logs["endpoint"][current_size] = endpoint
            audit_logs["payload_hash"][current_size] = payload_hash
            audit_logs["result_hash"][current_size] = result_hash
            audit_logs["status"][current_size] = status
            audit_logs["metadata"][current_size] = metadata_str

        logger.info(
            "AUDIT_LOG_APPENDED",
            audit_id=audit_id,
            operation=operation,
            user_id=user_id,
            endpoint=endpoint,
            status=status
        )

        return audit_id

    except (IOError, OSError, ValueError, TypeError, KeyError) as e:
        logger.error(
            "AUDIT_LOG_APPEND_FAILED",
            error=str(e),
            operation=operation,
            user_id=user_id
        )
        raise


def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: Optional[str] = None,
    user_filter: Optional[str] = None
) -> List[Dict]:
    """
    Retrieve audit logs with optional filters.

    Args:
        corpus_path: Path to corpus
        limit: Maximum number of logs to retrieve
        operation_filter: Filter by operation name
        user_filter: Filter by user_id

    Returns:
        List of audit log dictionaries

    Examples:
        >>> logs = get_audit_logs("storage/corpus.h5", limit=10)
        >>> logs = get_audit_logs("storage/corpus.h5", operation_filter="INTERACTION_APPENDED")
    """
    try:
        with h5py.File(corpus_path, 'r') as f:
            if "audit_logs" not in f:
                return []

            audit_logs_group = f["audit_logs"]
            total = audit_logs_group["audit_id"].shape[0]

            if total == 0:
                return []

            # Read from end (most recent first)
            start = max(0, total - limit)
            end = total

            results = []
            for i in range(end - 1, start - 1, -1):  # Reverse order
                # Apply filters
                operation = audit_logs_group["operation"][i].decode('utf-8')
                user_id = audit_logs_group["user_id"][i].decode('utf-8')

                if operation_filter and operation != operation_filter:
                    continue

                if user_filter and user_id != user_filter:
                    continue

                log_entry = {
                    "audit_id": audit_logs_group["audit_id"][i].decode('utf-8'),
                    "timestamp": audit_logs_group["timestamp"][i].decode('utf-8'),
                    "operation": operation,
                    "user_id": user_id,
                    "endpoint": audit_logs_group["endpoint"][i].decode('utf-8'),
                    "payload_hash": audit_logs_group["payload_hash"][i].decode('utf-8'),
                    "result_hash": audit_logs_group["result_hash"][i].decode('utf-8'),
                    "status": audit_logs_group["status"][i].decode('utf-8'),
                    "metadata": audit_logs_group["metadata"][i].decode('utf-8')
                }
                results.append(log_entry)

            return results

    except (IOError, OSError, KeyError) as e:
        from backend.logger import get_logger
        logger = get_logger()
        logger.error("AUDIT_LOGS_READ_FAILED", error=str(e))
        return []


def get_audit_stats(corpus_path: str) -> Dict:
    """
    Get audit log statistics.

    Args:
        corpus_path: Path to corpus

    Returns:
        Dictionary with stats

    Examples:
        >>> stats = get_audit_stats("storage/corpus.h5")
        >>> print(stats["total_logs"])
    """
    try:
        with h5py.File(corpus_path, 'r') as f:
            if "audit_logs" not in f:
                return {"total_logs": 0, "exists": False}

            audit_logs = f["audit_logs"]
            total = audit_logs["audit_id"].shape[0]

            # Count by status
            status_counts = {}
            operation_counts = {}

            for i in range(total):
                status = audit_logs["status"][i].decode('utf-8')
                operation = audit_logs["operation"][i].decode('utf-8')

                status_counts[status] = status_counts.get(status, 0) + 1
                operation_counts[operation] = operation_counts.get(operation, 0) + 1

            return {
                "total_logs": total,
                "exists": True,
                "status_breakdown": status_counts,
                "operation_breakdown": operation_counts
            }

    except (IOError, OSError, KeyError) as e:
        from backend.logger import get_logger
        logger = get_logger()
        logger.error("AUDIT_STATS_FAILED", error=str(e))
        return {"total_logs": 0, "exists": False, "error": str(e)}


def get_audit_logs_older_than(corpus_path: str, days: int = 90) -> List[int]:
    """
    Get indices of audit logs older than specified days.

    Args:
        corpus_path: Path to corpus.h5
        days: Age threshold in days (default: 90)

    Returns:
        List of indices for logs older than threshold

    Examples:
        >>> old_indices = get_audit_logs_older_than("storage/corpus.h5", days=90)
        >>> print(f"Found {len(old_indices)} logs older than 90 days")
    """
    from datetime import datetime, timedelta

    try:
        with h5py.File(corpus_path, 'r') as f:
            if "audit_logs" not in f:
                return []

            audit_logs = f["audit_logs"]
            total = audit_logs["timestamp"].shape[0]

            if total == 0:
                return []

            # Calculate cutoff date
            cutoff_date = datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=days)

            # Find old logs
            old_indices = []
            for i in range(total):
                timestamp_str = audit_logs["timestamp"][i].decode('utf-8')
                log_date = datetime.fromisoformat(timestamp_str)

                if log_date < cutoff_date:
                    old_indices.append(i)

            return old_indices

    except Exception as e:
        from backend.logger import get_logger
        logger = get_logger()
        logger.error("RETENTION_CHECK_FAILED", error=str(e))
        return []


def cleanup_old_audit_logs(corpus_path: str, days: int = 90, dry_run: bool = True) -> Dict:
    """
    Remove audit logs older than specified days.

    ⚠️  POLICY VIOLATION WARNING ⚠️
    This function VIOLATES the append-only policy by physically deleting audit log entries.
    It is provided for compliance with data retention regulations (e.g., GDPR Article 17).

    TRADE-OFF:
    - ✅ Compliance: Meets legal requirements for data retention limits
    - ❌ Immutability: Breaks non-repudiation guarantee for deleted logs
    - ❌ Audit Trail: Deletion operation itself is logged, but deleted logs are gone

    ALTERNATIVES (for future consideration):
    1. Logical deletion: Add "archived_at" field, mark rows as ARCHIVED instead of deleting
    2. Separate archive: Move old logs to separate HDF5 file
    3. Compliance flag: Add "retention_compliant" attribute, query by date

    RECOMMENDATION:
    Use dry_run=True first to understand impact. Document deletion in external audit system.

    IMPORTANT: This is a DESTRUCTIVE operation. Use dry_run=True first.

    Args:
        corpus_path: Path to corpus.h5
        days: Retention period in days (default: 90)
        dry_run: If True, only report what would be deleted (default: True)

    Returns:
        Dictionary with cleanup results

    Examples:
        >>> # Check what would be deleted
        >>> result = cleanup_old_audit_logs("storage/corpus.h5", days=90, dry_run=True)
        >>> print(f"Would delete {result['would_delete']} logs")
        >>>
        >>> # Actually delete (CAREFUL!)
        >>> result = cleanup_old_audit_logs("storage/corpus.h5", days=90, dry_run=False)
    """
    from backend.logger import get_logger
    from datetime import datetime, timedelta

    logger = get_logger()

    try:
        old_indices = get_audit_logs_older_than(corpus_path, days)

        if dry_run:
            logger.info(
                "RETENTION_DRY_RUN",
                would_delete=len(old_indices),
                retention_days=days,
                corpus_path=corpus_path
            )
            return {
                "dry_run": True,
                "would_delete": len(old_indices),
                "retention_days": days,
                "cutoff_date": (datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=days)).isoformat()
            }

        # Actually delete old logs
        if len(old_indices) == 0:
            logger.info("RETENTION_CLEANUP_NOTHING_TO_DELETE", retention_days=days)
            return {
                "dry_run": False,
                "deleted": 0,
                "retention_days": days
            }

        # NOTE: HDF5 doesn't support in-place deletion of rows
        # We need to create new datasets without old rows
        with h5py.File(corpus_path, 'a') as f:
            audit_logs = f["audit_logs"]
            total = audit_logs["timestamp"].shape[0]

            # Indices to keep
            keep_indices = [i for i in range(total) if i not in old_indices]

            # Create temporary datasets with kept data
            for dataset_name in AUDIT_LOG_SCHEMA.keys():
                dataset = audit_logs[dataset_name]

                # Read data to keep
                kept_data = [dataset[i] for i in keep_indices]

                # Delete old dataset
                del audit_logs[dataset_name]

                # Create new dataset with kept data only
                spec = AUDIT_LOG_SCHEMA[dataset_name]
                new_dataset = audit_logs.create_dataset(
                    dataset_name,
                    shape=(len(kept_data),),
                    maxshape=(None,),
                    dtype=spec["dtype"],
                    chunks=True,
                    compression="gzip",
                    compression_opts=4
                )

                # Write kept data
                if len(kept_data) > 0:
                    for i, value in enumerate(kept_data):
                        new_dataset[i] = value

        logger.info(
            "RETENTION_CLEANUP_COMPLETED",
            deleted=len(old_indices),
            kept=len(keep_indices),
            retention_days=days
        )

        return {
            "dry_run": False,
            "deleted": len(old_indices),
            "kept": len(keep_indices),
            "retention_days": days
        }

    except Exception as e:
        logger.error("RETENTION_CLEANUP_FAILED", error=str(e))
        return {
            "dry_run": dry_run,
            "error": str(e),
            "deleted": 0
        }


def get_retention_stats(corpus_path: str, retention_days: int = 90) -> Dict:
    """
    Get statistics about audit log retention.

    Args:
        corpus_path: Path to corpus.h5
        retention_days: Retention period to check (default: 90)

    Returns:
        Dictionary with retention statistics

    Examples:
        >>> stats = get_retention_stats("storage/corpus.h5", retention_days=90)
        >>> print(f"Total logs: {stats['total_logs']}")
        >>> print(f"Within retention: {stats['within_retention']}")
        >>> print(f"Beyond retention: {stats['beyond_retention']}")
    """
    from datetime import datetime, timedelta

    try:
        old_indices = get_audit_logs_older_than(corpus_path, retention_days)

        with h5py.File(corpus_path, 'r') as f:
            if "audit_logs" not in f:
                return {
                    "exists": False,
                    "total_logs": 0,
                    "within_retention": 0,
                    "beyond_retention": 0,
                    "retention_days": retention_days
                }

            total = f["audit_logs"]["timestamp"].shape[0]
            beyond_retention = len(old_indices)
            within_retention = total - beyond_retention

            cutoff_date = datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=retention_days)

            # Get oldest and newest log dates
            oldest_log = None
            newest_log = None

            if total > 0:
                oldest_log = f["audit_logs"]["timestamp"][0].decode('utf-8')
                newest_log = f["audit_logs"]["timestamp"][total - 1].decode('utf-8')

            return {
                "exists": True,
                "total_logs": total,
                "within_retention": within_retention,
                "beyond_retention": beyond_retention,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "oldest_log": oldest_log,
                "newest_log": newest_log,
                "percentage_old": (beyond_retention / total * 100) if total > 0 else 0
            }

    except Exception as e:
        from backend.logger import get_logger
        logger = get_logger()
        logger.error("RETENTION_STATS_FAILED", error=str(e))
        return {
            "exists": False,
            "error": str(e),
            "total_logs": 0
        }


if __name__ == "__main__":
    """Demo: Audit logs"""
    from config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    print("🔒 Audit Logs Demo - Free Intelligence\n")

    # Initialize audit_logs group
    print("Initializing audit_logs group...")
    init_audit_logs_group(corpus_path)

    # Append test audit log
    print("\nAppending test audit log...")
    audit_id = append_audit_log(
        corpus_path,
        operation="TEST_OPERATION",
        user_id="demo_user",
        endpoint="audit_logs_demo",
        payload={"action": "test", "data": "sample"},
        result={"success": True},
        status="SUCCESS",
        metadata={"source": "demo"}
    )
    print(f"  Audit ID: {audit_id}")

    # Get stats
    print("\n📊 Audit Log Statistics:")
    stats = get_audit_stats(corpus_path)
    print(f"  Total logs: {stats['total_logs']}")
    print(f"  Status breakdown: {stats.get('status_breakdown', {})}")

    # Get recent logs
    print("\n📖 Recent Audit Logs:")
    logs = get_audit_logs(corpus_path, limit=5)
    for i, log in enumerate(logs, 1):
        print(f"\n  [{i}] {log['timestamp']}")
        print(f"      Operation: {log['operation']}")
        print(f"      User: {log['user_id']}")
        print(f"      Status: {log['status']}")
        print(f"      Payload hash: {log['payload_hash'][:16]}...")
