#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Log Manifest (Chained Daily Hash)

Manifest encadenado diario para audit logs:
- Hash SHA256 de todos los access/* del día
- Hash del manifest anterior (blockchain-style chain)
- Garantía de integridad y non-repudiation

FI-CORE-FEAT-003
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from packages.fi_common.logging.log_rotation import LogRotation
from packages.fi_common.logging.logger_structured import ServiceChannel


class LogManifest:
    """
    Gestiona manifests encadenados diarios para audit logs.

    Cada manifest contiene:
    - date: Fecha del manifest (YYYY-MM-DD)
    - access_log_hash: SHA256 de todos los eventos access/* del día
    - event_count: Número de eventos
    - previous_manifest_hash: Hash del manifest anterior (blockchain chain)
    - manifest_hash: SHA256 del propio manifest
    """

    def __init__(self, base_path: str = "data/logs"):
        """
        Initialize manifest manager.

        Args:
            base_path: Base path para logs
        """
        self.rotation = LogRotation(base_path=base_path)
        self.manifest_path = self.rotation.base_path / "manifest"
        self.manifest_path.mkdir(parents=True, exist_ok=True)

    def compute_access_log_hash(self, date: str) -> tuple[str, int]:
        """
        Compute SHA256 hash of all access log events for a date.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Tuple of (hash, event_count)
        """
        # Get access log file for date
        access_path = self.rotation.get_compressed_log_path(ServiceChannel.ACCESS, date)

        if not access_path.exists():
            # Try uncompressed
            access_path = self.rotation.base_path / ServiceChannel.ACCESS.value / f"{date}.ndjson"
            if not access_path.exists():
                return hashlib.sha256(b"").hexdigest(), 0

        # Read all events
        events = self.rotation.read_log_file(access_path)

        if not events:
            return hashlib.sha256(b"").hexdigest(), 0

        # Concatenate all event hashes
        concatenated = "".join(
            hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
            for event in events
        )

        # Final hash
        final_hash = hashlib.sha256(concatenated.encode()).hexdigest()

        return final_hash, len(events)

    def get_previous_manifest_hash(self, current_date: str) -> Optional[str]:
        """
        Get hash of previous day's manifest.

        Args:
            current_date: Current date (YYYY-MM-DD)

        Returns:
            Previous manifest hash or None if first manifest
        """
        # Parse current date
        current = datetime.strptime(current_date, "%Y-%m-%d")

        # Find previous date with manifest
        for days_back in range(1, 365):  # Search up to 1 year back
            prev_date = current - timedelta(days=days_back)
            prev_date_str = prev_date.strftime("%Y-%m-%d")
            prev_manifest_path = self.manifest_path / f"daily-{prev_date_str}.json"

            if prev_manifest_path.exists():
                with open(prev_manifest_path) as f:
                    prev_manifest = json.load(f)
                    return prev_manifest.get("manifest_hash")

        return None

    def create_daily_manifest(self, date: Optional[str] = None) -> dict[str, Any]:
        """
        Create daily manifest for date.

        Args:
            date: Date string (YYYY-MM-DD), defaults to yesterday

        Returns:
            Manifest dict
        """
        if date is None:
            # Default to yesterday (since we manifest after day ends)
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")

        # Compute access log hash
        access_hash, event_count = self.compute_access_log_hash(date)

        # Get previous manifest hash
        prev_hash = self.get_previous_manifest_hash(date)

        # Create manifest
        manifest = {
            "date": date,
            "access_log_hash": access_hash,
            "event_count": event_count,
            "previous_manifest_hash": prev_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Compute manifest hash
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest["manifest_hash"] = hashlib.sha256(manifest_str.encode()).hexdigest()

        # Save manifest
        manifest_file = self.manifest_path / f"daily-{date}.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return manifest

    def verify_manifest_chain(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Verify integrity of manifest chain.

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to oldest manifest
            end_date: End date (YYYY-MM-DD), defaults to newest manifest

        Returns:
            Verification result dict
        """
        # Get all manifests
        manifest_files = sorted(self.manifest_path.glob("daily-*.json"))

        if not manifest_files:
            return {"valid": True, "manifests_checked": 0, "errors": []}

        manifests = []
        for manifest_file in manifest_files:
            with open(manifest_file) as f:
                manifests.append(json.load(f))

        # Filter by date range
        if start_date:
            manifests = [m for m in manifests if m["date"] >= start_date]
        if end_date:
            manifests = [m for m in manifests if m["date"] <= end_date]

        # Sort by date
        manifests.sort(key=lambda m: m["date"])

        errors = []
        prev_hash = None

        for i, manifest in enumerate(manifests):
            date = manifest["date"]

            # Check 1: Manifest hash is valid
            manifest_copy = manifest.copy()
            expected_hash = manifest_copy.pop("manifest_hash")
            computed_hash = hashlib.sha256(
                json.dumps(manifest_copy, sort_keys=True).encode()
            ).hexdigest()

            if expected_hash != computed_hash:
                errors.append(
                    {
                        "date": date,
                        "error": "manifest_hash_mismatch",
                        "expected": expected_hash,
                        "computed": computed_hash,
                    }
                )

            # Check 2: Previous manifest hash matches chain
            if i > 0:
                if manifest["previous_manifest_hash"] != prev_hash:
                    errors.append(
                        {
                            "date": date,
                            "error": "chain_broken",
                            "expected_prev_hash": prev_hash,
                            "found_prev_hash": manifest["previous_manifest_hash"],
                        }
                    )

            # Check 3: Access log hash is valid (re-compute)
            recomputed_access_hash, recomputed_count = self.compute_access_log_hash(date)

            if recomputed_access_hash != manifest["access_log_hash"]:
                errors.append(
                    {
                        "date": date,
                        "error": "access_log_hash_mismatch",
                        "expected": manifest["access_log_hash"],
                        "recomputed": recomputed_access_hash,
                    }
                )

            if recomputed_count != manifest["event_count"]:
                errors.append(
                    {
                        "date": date,
                        "error": "event_count_mismatch",
                        "expected": manifest["event_count"],
                        "recomputed": recomputed_count,
                    }
                )

            prev_hash = manifest["manifest_hash"]

        return {"valid": len(errors) == 0, "manifests_checked": len(manifests), "errors": errors}

    def get_manifest_stats(self) -> dict[str, Any]:
        """
        Get statistics about manifests.

        Returns:
            Stats dict
        """
        manifest_files = list(self.manifest_path.glob("daily-*.json"))

        if not manifest_files:
            return {
                "manifest_count": 0,
                "oldest_date": None,
                "newest_date": None,
                "total_events": 0,
            }

        manifests = []
        for manifest_file in manifest_files:
            with open(manifest_file) as f:
                manifests.append(json.load(f))

        dates = [m["date"] for m in manifests]
        total_events = sum(m["event_count"] for m in manifests)

        return {
            "manifest_count": len(manifests),
            "oldest_date": min(dates),
            "newest_date": max(dates),
            "total_events": total_events,
        }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    print("🔗 FREE INTELLIGENCE - LOG MANIFEST (CHAINED)")
    print("=" * 60)
    print()

    manifest_mgr = LogManifest(base_path="data/logs")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "create":
            # Create manifest for date (default yesterday)
            date = sys.argv[2] if len(sys.argv) > 2 else None
            manifest = manifest_mgr.create_daily_manifest(date)
            print(f"✅ Created manifest for {manifest['date']}")
            print(f"   Access log hash: {manifest['access_log_hash'][:16]}...")
            print(f"   Event count: {manifest['event_count']}")
            print(
                f"   Previous manifest: {manifest['previous_manifest_hash'][:16] if manifest['previous_manifest_hash'] else 'None'}..."
            )
            print(f"   Manifest hash: {manifest['manifest_hash'][:16]}...")

        elif command == "verify":
            # Verify manifest chain
            result = manifest_mgr.verify_manifest_chain()
            if result["valid"]:
                print(f"✅ VALID - All {result['manifests_checked']} manifests verified")
            else:
                print(f"❌ INVALID - Found {len(result['errors'])} errors")
                for error in result["errors"]:
                    print(f"   [{error['date']}] {error['error']}")

        elif command == "stats":
            # Show manifest stats
            stats = manifest_mgr.get_manifest_stats()
            print("📊 Manifest Stats:")
            print(f"   Total manifests: {stats['manifest_count']}")
            print(f"   Oldest: {stats['oldest_date']}")
            print(f"   Newest: {stats['newest_date']}")
            print(f"   Total events: {stats['total_events']}")

        else:
            print(f"Unknown command: {command}")
            print("Usage:")
            print("   python3 log_manifest.py create [date]  # Create manifest")
            print("   python3 log_manifest.py verify         # Verify chain")
            print("   python3 log_manifest.py stats          # Show stats")

    else:
        print("Usage:")
        print(
            "   python3 log_manifest.py create [YYYY-MM-DD]  # Create manifest (default: yesterday)"
        )
        print("   python3 log_manifest.py verify                # Verify manifest chain")
        print("   python3 log_manifest.py stats                 # Show manifest statistics")
        print()
        print("Examples:")
        print("   python3 log_manifest.py create 2025-10-27")
        print("   python3 log_manifest.py verify")
