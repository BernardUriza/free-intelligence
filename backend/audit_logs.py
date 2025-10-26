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
from typing import Dict, Optional, List
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
    from logger import get_logger

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

    except Exception as e:
        logger.error("AUDIT_LOGS_INIT_FAILED", error=str(e), path=corpus_path)
        return False


def hash_payload(payload: any) -> str:
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
    from logger import get_logger
    from append_only_policy import AppendOnlyPolicy
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

    except Exception as e:
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

    except Exception as e:
        from logger import get_logger
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

    except Exception as e:
        from logger import get_logger
        logger = get_logger()
        logger.error("AUDIT_STATS_FAILED", error=str(e))
        return {"total_logs": 0, "exists": False, "error": str(e)}


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
