"""
Tests para Audit Log Retention Policy

Cobertura:
- get_audit_logs_older_than()
- cleanup_old_audit_logs() (dry run y real)
- get_retention_stats()
- Retención de 90 días por defecto
- Dry run no modifica datos

Autor: Bernard Uriza Orozco
Fecha: 2025-10-26
Task: FI-DATA-FEAT-007
"""

import os

# Add backend to path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import h5py

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from audit_logs import (
    append_audit_log,
    cleanup_old_audit_logs,
    get_audit_logs_older_than,
    get_retention_stats,
    init_audit_logs_group,
)


class TestAuditLogRetention(unittest.TestCase):
    """Tests para política de retención de audit logs."""

    def setUp(self) -> None:
        """Create temporary HDF5 file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".h5")
        self.corpus_path = self.temp_file.name
        self.temp_file.close()

        # Initialize minimal corpus structure
        with h5py.File(self.corpus_path, "w") as f:
            metadata = f.create_group("metadata")
            metadata.attrs["created_at"] = datetime.now(ZoneInfo("America/Mexico_City")).isoformat()
            metadata.attrs["version"] = "0.1.0"

        # Initialize audit_logs group
        init_audit_logs_group(self.corpus_path)

    def tearDown(self) -> None:
        """Remove temporary file."""
        if os.path.exists(self.corpus_path):
            os.unlink(self.corpus_path)

    def test_get_audit_logs_older_than_empty(self) -> None:
        """Debe retornar lista vacía si no hay logs."""
        old_indices = get_audit_logs_older_than(self.corpus_path, days=90)

        self.assertEqual(len(old_indices), 0)

    def test_get_audit_logs_older_than_all_recent(self) -> None:
        """Debe retornar lista vacía si todos los logs son recientes."""
        # Append recent log
        append_audit_log(
            self.corpus_path,
            operation="TEST_OP",
            user_id="test_user",
            endpoint="test",
            payload={"test": "data"},
            result={"success": True},
        )

        old_indices = get_audit_logs_older_than(self.corpus_path, days=90)

        self.assertEqual(len(old_indices), 0)

    def test_get_audit_logs_older_than_with_old_logs(self) -> None:
        """Debe detectar logs antiguos correctamente."""
        # Manually insert old log (100 days ago)
        old_timestamp = (
            datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=100)
        ).isoformat()

        with h5py.File(self.corpus_path, "a") as f:
            audit_logs = f["audit_logs"]

            # Resize datasets
            for dataset_name in audit_logs.keys():
                audit_logs[dataset_name].resize((1,))

            # Write old log
            audit_logs["audit_id"][0] = "old-log-id"
            audit_logs["timestamp"][0] = old_timestamp
            audit_logs["operation"][0] = "OLD_OP"
            audit_logs["user_id"][0] = "old_user"
            audit_logs["endpoint"][0] = "old_endpoint"
            audit_logs["payload_hash"][0] = "0" * 64
            audit_logs["result_hash"][0] = "0" * 64
            audit_logs["status"][0] = "COMPLETED"
            audit_logs["metadata"][0] = "{}"

        # Check detection
        old_indices = get_audit_logs_older_than(self.corpus_path, days=90)

        self.assertEqual(len(old_indices), 1)
        self.assertEqual(old_indices[0], 0)

    def test_cleanup_old_audit_logs_dry_run(self) -> None:
        """Dry run no debe modificar datos."""
        # Insert old log
        old_timestamp = (
            datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=100)
        ).isoformat()

        with h5py.File(self.corpus_path, "a") as f:
            audit_logs = f["audit_logs"]
            for dataset_name in audit_logs.keys():
                audit_logs[dataset_name].resize((1,))
            audit_logs["timestamp"][0] = old_timestamp
            audit_logs["audit_id"][0] = "old-log"
            audit_logs["operation"][0] = "OLD_OP"
            audit_logs["user_id"][0] = "user"
            audit_logs["endpoint"][0] = "endpoint"
            audit_logs["payload_hash"][0] = "0" * 64
            audit_logs["result_hash"][0] = "0" * 64
            audit_logs["status"][0] = "COMPLETED"
            audit_logs["metadata"][0] = "{}"

        # Dry run
        result = cleanup_old_audit_logs(self.corpus_path, days=90, dry_run=True)

        # Verify result
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_delete"], 1)

        # Verify data not modified
        with h5py.File(self.corpus_path, "r") as f:
            total = f["audit_logs"]["timestamp"].shape[0]
            self.assertEqual(total, 1, "Dry run should not delete data")

    def test_cleanup_old_audit_logs_actual_cleanup(self) -> None:
        """Cleanup real debe eliminar logs antiguos."""
        # Insert 1 old log and 1 recent log
        old_timestamp = (
            datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=100)
        ).isoformat()
        recent_timestamp = datetime.now(ZoneInfo("America/Mexico_City")).isoformat()

        with h5py.File(self.corpus_path, "a") as f:
            audit_logs = f["audit_logs"]

            # Resize to 2 logs
            for dataset_name in audit_logs.keys():
                audit_logs[dataset_name].resize((2,))

            # Old log
            audit_logs["timestamp"][0] = old_timestamp
            audit_logs["audit_id"][0] = "old-log"
            audit_logs["operation"][0] = "OLD_OP"
            audit_logs["user_id"][0] = "old_user"
            audit_logs["endpoint"][0] = "old"
            audit_logs["payload_hash"][0] = "0" * 64
            audit_logs["result_hash"][0] = "0" * 64
            audit_logs["status"][0] = "COMPLETED"
            audit_logs["metadata"][0] = "{}"

            # Recent log
            audit_logs["timestamp"][1] = recent_timestamp
            audit_logs["audit_id"][1] = "recent-log"
            audit_logs["operation"][1] = "RECENT_OP"
            audit_logs["user_id"][1] = "recent_user"
            audit_logs["endpoint"][1] = "recent"
            audit_logs["payload_hash"][1] = "1" * 64
            audit_logs["result_hash"][1] = "1" * 64
            audit_logs["status"][1] = "COMPLETED"
            audit_logs["metadata"][1] = "{}"

        # Actual cleanup
        result = cleanup_old_audit_logs(self.corpus_path, days=90, dry_run=False)

        # Verify result
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["deleted"], 1)
        self.assertEqual(result["kept"], 1)

        # Verify only recent log remains
        with h5py.File(self.corpus_path, "r") as f:
            total = f["audit_logs"]["timestamp"].shape[0]
            self.assertEqual(total, 1)

            remaining_id = f["audit_logs"]["audit_id"][0].decode("utf-8")
            self.assertEqual(remaining_id, "recent-log")

    def test_cleanup_old_audit_logs_nothing_to_delete(self) -> None:
        """Si no hay logs antiguos, no debe hacer nada."""
        # Insert recent log
        append_audit_log(
            self.corpus_path,
            operation="RECENT_OP",
            user_id="user",
            endpoint="test",
            payload={"test": "data"},
            result={"success": True},
        )

        # Try cleanup
        result = cleanup_old_audit_logs(self.corpus_path, days=90, dry_run=False)

        self.assertEqual(result["deleted"], 0)

        # Verify log still exists
        with h5py.File(self.corpus_path, "r") as f:
            total = f["audit_logs"]["timestamp"].shape[0]
            self.assertEqual(total, 1)

    def test_get_retention_stats_empty(self) -> None:
        """Debe manejar caso de no logs."""
        stats = get_retention_stats(self.corpus_path, retention_days=90)

        self.assertTrue(stats["exists"])
        self.assertEqual(stats["total_logs"], 0)
        self.assertEqual(stats["within_retention"], 0)
        self.assertEqual(stats["beyond_retention"], 0)

    def test_get_retention_stats_with_mixed_logs(self) -> None:
        """Debe calcular stats correctamente con logs mixtos."""
        # Insert 2 old logs and 3 recent logs
        now = datetime.now(ZoneInfo("America/Mexico_City"))
        old_timestamp = (now - timedelta(days=100)).isoformat()
        recent_timestamp = now.isoformat()

        with h5py.File(self.corpus_path, "a") as f:
            audit_logs = f["audit_logs"]

            # Resize to 5 logs
            for dataset_name in audit_logs.keys():
                audit_logs[dataset_name].resize((5,))

            # 2 old logs
            for i in range(2):
                audit_logs["timestamp"][i] = old_timestamp
                audit_logs["audit_id"][i] = f"old-log-{i}"
                audit_logs["operation"][i] = "OLD_OP"
                audit_logs["user_id"][i] = "old_user"
                audit_logs["endpoint"][i] = "old"
                audit_logs["payload_hash"][i] = "0" * 64
                audit_logs["result_hash"][i] = "0" * 64
                audit_logs["status"][i] = "COMPLETED"
                audit_logs["metadata"][i] = "{}"

            # 3 recent logs
            for i in range(2, 5):
                audit_logs["timestamp"][i] = recent_timestamp
                audit_logs["audit_id"][i] = f"recent-log-{i}"
                audit_logs["operation"][i] = "RECENT_OP"
                audit_logs["user_id"][i] = "recent_user"
                audit_logs["endpoint"][i] = "recent"
                audit_logs["payload_hash"][i] = "1" * 64
                audit_logs["result_hash"][i] = "1" * 64
                audit_logs["status"][i] = "COMPLETED"
                audit_logs["metadata"][i] = "{}"

        # Get stats
        stats = get_retention_stats(self.corpus_path, retention_days=90)

        self.assertEqual(stats["total_logs"], 5)
        self.assertEqual(stats["within_retention"], 3)
        self.assertEqual(stats["beyond_retention"], 2)
        self.assertEqual(stats["retention_days"], 90)
        self.assertAlmostEqual(stats["percentage_old"], 40.0, places=1)
        self.assertIsNotNone(stats["oldest_log"])
        self.assertIsNotNone(stats["newest_log"])

    def test_custom_retention_days(self) -> None:
        """Debe respetar período de retención custom."""
        # Insert log 50 days old
        timestamp_50_days = (
            datetime.now(ZoneInfo("America/Mexico_City")) - timedelta(days=50)
        ).isoformat()

        with h5py.File(self.corpus_path, "a") as f:
            audit_logs = f["audit_logs"]
            for dataset_name in audit_logs.keys():
                audit_logs[dataset_name].resize((1,))
            audit_logs["timestamp"][0] = timestamp_50_days
            audit_logs["audit_id"][0] = "log-50-days"
            audit_logs["operation"][0] = "OP"
            audit_logs["user_id"][0] = "user"
            audit_logs["endpoint"][0] = "endpoint"
            audit_logs["payload_hash"][0] = "0" * 64
            audit_logs["result_hash"][0] = "0" * 64
            audit_logs["status"][0] = "COMPLETED"
            audit_logs["metadata"][0] = "{}"

        # With 90 days retention, should not be old
        old_indices_90 = get_audit_logs_older_than(self.corpus_path, days=90)
        self.assertEqual(len(old_indices_90), 0)

        # With 30 days retention, should be old
        old_indices_30 = get_audit_logs_older_than(self.corpus_path, days=30)
        self.assertEqual(len(old_indices_30), 1)


if __name__ == "__main__":
    unittest.main()
