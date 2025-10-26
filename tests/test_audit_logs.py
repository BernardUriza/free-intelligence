#!/usr/bin/env python3
"""
Tests for Audit Logs

FI-SEC-FEAT-003
"""

import unittest
import tempfile
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from corpus_schema import init_corpus
from audit_logs import (
    init_audit_logs_group,
    hash_payload,
    append_audit_log,
    get_audit_logs,
    get_audit_stats,
    AUDIT_LOG_SCHEMA
)


class TestAuditLogs(unittest.TestCase):
    """Test audit logs functionality."""

    temp_dir: str
    corpus_path: str

    def setUp(self):
        """Create temporary corpus for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.corpus_path = os.path.join(self.temp_dir, "test_corpus.h5")

        # Initialize corpus
        init_corpus(self.corpus_path, owner_identifier="test@example.com")

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.corpus_path):
            os.remove(self.corpus_path)
        os.rmdir(self.temp_dir)

    def test_init_audit_logs_group(self):
        """Test initialization of audit_logs group."""
        result = init_audit_logs_group(self.corpus_path)
        self.assertTrue(result)

        # Verify group exists
        import h5py
        with h5py.File(self.corpus_path, 'r') as f:
            self.assertIn("audit_logs", f)

            audit_logs = f["audit_logs"]
            for dataset_name in AUDIT_LOG_SCHEMA.keys():
                self.assertIn(dataset_name, audit_logs)

    def test_init_audit_logs_group_idempotent(self):
        """Test that initializing twice is safe."""
        result1 = init_audit_logs_group(self.corpus_path)
        result2 = init_audit_logs_group(self.corpus_path)

        self.assertTrue(result1)
        self.assertTrue(result2)

    def test_hash_payload_dict(self):
        """Test hashing of dictionary payload."""
        payload1 = {"user": "bernard", "action": "test"}
        payload2 = {"action": "test", "user": "bernard"}  # Different order

        hash1 = hash_payload(payload1)
        hash2 = hash_payload(payload2)

        # Should be same (sorted keys)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length

    def test_hash_payload_string(self):
        """Test hashing of string payload."""
        payload = "test_string"
        hash_result = hash_payload(payload)

        self.assertEqual(len(hash_result), 64)
        self.assertIsInstance(hash_result, str)

    def test_hash_payload_none(self):
        """Test hashing of None."""
        hash_result = hash_payload(None)
        self.assertEqual(len(hash_result), 64)

    def test_append_audit_log(self):
        """Test appending audit log entry."""
        # Init audit logs
        init_audit_logs_group(self.corpus_path)

        # Append log
        audit_id = append_audit_log(
            self.corpus_path,
            operation="TEST_OPERATION",
            user_id="test_user",
            endpoint="test_endpoint",
            payload={"key": "value"},
            result={"success": True},
            status="SUCCESS",
            metadata={"source": "test"}
        )

        self.assertIsNotNone(audit_id)
        self.assertEqual(len(audit_id), 36)  # UUID length

    def test_append_audit_log_without_init(self):
        """Test that appending auto-initializes if needed."""
        # Don't init explicitly
        audit_id = append_audit_log(
            self.corpus_path,
            operation="AUTO_INIT_TEST",
            user_id="test_user",
            endpoint="test_endpoint"
        )

        self.assertIsNotNone(audit_id)

    def test_append_multiple_logs(self):
        """Test appending multiple audit logs."""
        init_audit_logs_group(self.corpus_path)

        # Append 5 logs
        for i in range(5):
            append_audit_log(
                self.corpus_path,
                operation=f"TEST_OPERATION_{i}",
                user_id=f"user_{i}",
                endpoint="test_endpoint",
                status="SUCCESS"
            )

        # Verify count
        stats = get_audit_stats(self.corpus_path)
        self.assertEqual(stats["total_logs"], 5)

    def test_get_audit_logs(self):
        """Test retrieving audit logs."""
        init_audit_logs_group(self.corpus_path)

        # Append test log
        append_audit_log(
            self.corpus_path,
            operation="TEST_READ",
            user_id="test_user",
            endpoint="test_endpoint",
            payload={"test": "data"},
            status="SUCCESS"
        )

        # Retrieve logs
        logs = get_audit_logs(self.corpus_path, limit=10)

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["operation"], "TEST_READ")
        self.assertEqual(logs[0]["user_id"], "test_user")
        self.assertEqual(logs[0]["status"], "SUCCESS")

    def test_get_audit_logs_empty(self):
        """Test retrieving from empty audit logs."""
        init_audit_logs_group(self.corpus_path)

        logs = get_audit_logs(self.corpus_path, limit=10)
        self.assertEqual(len(logs), 0)

    def test_get_audit_logs_no_group(self):
        """Test retrieving when group doesn't exist."""
        logs = get_audit_logs(self.corpus_path, limit=10)
        self.assertEqual(len(logs), 0)

    def test_get_audit_logs_with_operation_filter(self):
        """Test filtering audit logs by operation."""
        init_audit_logs_group(self.corpus_path)

        # Append different operations
        append_audit_log(
            self.corpus_path,
            operation="OPERATION_A",
            user_id="user1",
            endpoint="test"
        )
        append_audit_log(
            self.corpus_path,
            operation="OPERATION_B",
            user_id="user1",
            endpoint="test"
        )
        append_audit_log(
            self.corpus_path,
            operation="OPERATION_A",
            user_id="user2",
            endpoint="test"
        )

        # Filter by OPERATION_A
        logs = get_audit_logs(
            self.corpus_path,
            limit=100,
            operation_filter="OPERATION_A"
        )

        self.assertEqual(len(logs), 2)
        for log in logs:
            self.assertEqual(log["operation"], "OPERATION_A")

    def test_get_audit_logs_with_user_filter(self):
        """Test filtering audit logs by user."""
        init_audit_logs_group(self.corpus_path)

        # Append different users
        append_audit_log(
            self.corpus_path,
            operation="TEST_OP",
            user_id="user_alice",
            endpoint="test"
        )
        append_audit_log(
            self.corpus_path,
            operation="TEST_OP",
            user_id="user_bob",
            endpoint="test"
        )

        # Filter by user_alice
        logs = get_audit_logs(
            self.corpus_path,
            limit=100,
            user_filter="user_alice"
        )

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["user_id"], "user_alice")

    def test_get_audit_stats(self):
        """Test getting audit statistics."""
        init_audit_logs_group(self.corpus_path)

        # Append logs with different statuses
        append_audit_log(
            self.corpus_path,
            operation="OP1",
            user_id="user1",
            endpoint="test",
            status="SUCCESS"
        )
        append_audit_log(
            self.corpus_path,
            operation="OP2",
            user_id="user1",
            endpoint="test",
            status="FAILED"
        )
        append_audit_log(
            self.corpus_path,
            operation="OP1",
            user_id="user2",
            endpoint="test",
            status="SUCCESS"
        )

        stats = get_audit_stats(self.corpus_path)

        self.assertEqual(stats["total_logs"], 3)
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["status_breakdown"]["SUCCESS"], 2)
        self.assertEqual(stats["status_breakdown"]["FAILED"], 1)
        self.assertEqual(stats["operation_breakdown"]["OP1"], 2)
        self.assertEqual(stats["operation_breakdown"]["OP2"], 1)

    def test_get_audit_stats_empty(self):
        """Test stats for empty audit logs."""
        init_audit_logs_group(self.corpus_path)

        stats = get_audit_stats(self.corpus_path)

        self.assertEqual(stats["total_logs"], 0)
        self.assertTrue(stats["exists"])

    def test_get_audit_stats_no_group(self):
        """Test stats when group doesn't exist."""
        stats = get_audit_stats(self.corpus_path)

        self.assertEqual(stats["total_logs"], 0)
        self.assertFalse(stats["exists"])

    def test_audit_log_fields(self):
        """Test that all required fields are present."""
        init_audit_logs_group(self.corpus_path)

        append_audit_log(
            self.corpus_path,
            operation="FIELD_TEST",
            user_id="test_user",
            endpoint="test_endpoint",
            payload={"data": "test"},
            result={"result": "ok"},
            status="SUCCESS",
            metadata={"meta": "data"}
        )

        logs = get_audit_logs(self.corpus_path, limit=1)
        log = logs[0]

        # Check all required fields
        self.assertIn("audit_id", log)
        self.assertIn("timestamp", log)
        self.assertIn("operation", log)
        self.assertIn("user_id", log)
        self.assertIn("endpoint", log)
        self.assertIn("payload_hash", log)
        self.assertIn("result_hash", log)
        self.assertIn("status", log)
        self.assertIn("metadata", log)

    def test_payload_hashing_consistency(self):
        """Test that payload hashing is consistent."""
        init_audit_logs_group(self.corpus_path)

        payload = {"user": "test", "action": "create"}

        # Append twice with same payload
        append_audit_log(
            self.corpus_path,
            operation="TEST1",
            user_id="user1",
            endpoint="test",
            payload=payload
        )
        append_audit_log(
            self.corpus_path,
            operation="TEST2",
            user_id="user1",
            endpoint="test",
            payload=payload
        )

        logs = get_audit_logs(self.corpus_path, limit=2)

        # Hashes should be identical
        self.assertEqual(logs[0]["payload_hash"], logs[1]["payload_hash"])


if __name__ == '__main__':
    unittest.main()
