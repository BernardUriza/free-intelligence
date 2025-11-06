#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Log Writer (Unified Interface)

Interfaz unificada para escribir logs con rotación automática.
Integra: logger_structured + log_rotation + log_manifest

FI-CORE-FEAT-003
"""

from pathlib import Path
from typing import Any, Literal, Optional

from log_manifest import LogManifest
from log_rotation import LogRotation
from logger_structured import (
    BaseLogEvent,
    ServiceChannel,
    UserRole,
    log_access_event,
    log_llm_request,
    log_server_request,
    log_storage_segment,
)


class LogWriter:
    """
    Unified log writer with automatic rotation.

    Usage:
        writer = LogWriter()

        # Write server log
        writer.write_server(
            method="POST",
            path="/api/consultations",
            status=201,
            ...
        )

        # Write LLM log
        writer.write_llm(
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            ...
        )

        # Write access log (AUDIT)
        writer.write_access(
            action="login",
            user="bernard@example.com",
            ...
        )
    """

    def __init__(self, base_path: str = "data/logs", auto_rotate: bool = True):
        """
        Initialize log writer.

        Args:
            base_path: Base path para logs
            auto_rotate: Auto-rotate logs when size/date threshold met
        """
        self.base_path = Path(base_path)
        self.rotation = LogRotation(base_path=str(base_path))
        self.manifest = LogManifest(base_path=str(base_path))
        self.auto_rotate = auto_rotate

    def _write_event(self, event: BaseLogEvent):
        """
        Write event to appropriate log file.

        Args:
            event: Log event to write
        """
        # Check if rotation needed
        if self.auto_rotate and self.rotation.should_rotate(event.service):
            self.rotation.rotate_log(event.service)

        # Get current log path
        log_path = self.rotation.get_current_log_path(event.service)

        # Append event
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(event.to_ndjson() + "\n")

    def write_server(
        self,
        method: str,
        path: str,
        status: int,
        bytes_sent: int,
        client_ip: str,
        latency_ms: float,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user: str = "system",
        role: UserRole = UserRole.SYSTEM,
    ):
        """Write server request log."""
        event = log_server_request(
            method=method,
            path=path,
            status=status,
            bytes_sent=bytes_sent,
            client_ip=client_ip,
            latency_ms=latency_ms,
            trace_id=trace_id,
            session_id=session_id,
            user=user,
            role=role,
        )
        self._write_event(event)

    def write_llm(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_est: float,
        prompt: str,
        response: str,
        latency_ms: float,
        sensitive: bool = False,
        timeout: bool = False,
        retry_count: int = 0,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user: str = "system",
        role: UserRole = UserRole.SYSTEM,
    ):
        """Write LLM request log."""
        event = log_llm_request(
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_est=cost_est,
            prompt=prompt,
            response=response,
            latency_ms=latency_ms,
            sensitive=sensitive,
            timeout=timeout,
            retry_count=retry_count,
            trace_id=trace_id,
            session_id=session_id,
            user=user,
            role=role,
        )
        self._write_event(event)

    def write_storage(
        self,
        file_path: str,
        sha256: str,
        segment_seconds: float,
        ready: bool,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user: str = "system",
    ):
        """Write storage segment log."""
        event = log_storage_segment(
            file_path=file_path,
            sha256=sha256,
            segment_seconds=segment_seconds,
            ready=ready,
            trace_id=trace_id,
            session_id=session_id,
            user=user,
        )
        self._write_event(event)

    def write_access(
        self,
        action: Literal["login", "logout", "role_change", "policy_update"],
        client_ip: str,
        result: bool,
        user: str,
        old_role: Optional[UserRole] = None,
        new_role: Optional[UserRole] = None,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: dict[str, Optional[Any]] = None,
    ):
        """Write access event log (AUDIT)."""
        event = log_access_event(
            action=action,
            client_ip=client_ip,
            result=result,
            user=user,
            old_role=old_role,
            new_role=new_role,
            trace_id=trace_id,
            session_id=session_id,
            details=details,
        )
        self._write_event(event)

    def rotate_all(self) -> dict[ServiceChannel, Optional[Path]]:
        """
        Rotate all logs.

        Returns:
            Dict mapping channel to compressed file path
        """
        results = {}
        for channel in ServiceChannel:
            compressed = self.rotation.rotate_log(channel)
            results[channel] = compressed
        return results

    def cleanup_all(self) -> dict[ServiceChannel, int]:
        """
        Cleanup old logs for all channels.

        Returns:
            Dict mapping channel to number of deleted files
        """
        results = {}
        for channel in ServiceChannel:
            deleted = self.rotation.cleanup_old_logs(channel)
            results[channel] = len(deleted)
        return results

    def create_manifest(self, date: Optional[str] = None) -> dict[str, Any]:
        """
        Create daily manifest for access logs.

        Args:
            date: Date (YYYY-MM-DD), defaults to yesterday

        Returns:
            Manifest dict
        """
        return self.manifest.create_daily_manifest(date)

    def verify_manifests(self) -> dict[str, Any]:
        """
        Verify manifest chain integrity.

        Returns:
            Verification result
        """
        return self.manifest.verify_manifest_chain()

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics for all logs and manifests.

        Returns:
            Stats dict with log_stats and manifest_stats
        """
        log_stats = {}
        for channel in ServiceChannel:
            log_stats[channel.value] = self.rotation.get_log_stats(channel)

        manifest_stats = self.manifest.get_manifest_stats()

        return {"log_stats": log_stats, "manifest_stats": manifest_stats}


# ============================================================================
# CLI Demo
# ============================================================================

if __name__ == "__main__":
    import sys
    import uuid

    print("📝 FREE INTELLIGENCE - LOG WRITER DEMO")
    print("=" * 60)
    print()

    writer = LogWriter(base_path="data/logs")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "demo":
            # Write sample logs to all channels
            trace_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            print("Writing demo logs...")
            print()

            # 1. Access log (login)
            print("1️⃣  Writing access log (login)...")
            writer.write_access(
                action="login",
                client_ip="192.168.1.100",
                result=True,
                user="bernard@example.com",
                trace_id=trace_id,
                session_id=session_id,
            )
            print("   ✅ Written to data/logs/access/")

            # 2. Server log
            print("2️⃣  Writing server log (API request)...")
            writer.write_server(
                method="POST",
                path="/api/consultations",
                status=201,
                bytes_sent=1024,
                client_ip="192.168.1.100",
                latency_ms=45.3,
                trace_id=trace_id,
                session_id=session_id,
                user="bernard@example.com",
                role=UserRole.OWNER,
            )
            print("   ✅ Written to data/logs/server/")

            # 3. LLM log
            print("3️⃣  Writing LLM log (Claude request)...")
            writer.write_llm(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                tokens_in=100,
                tokens_out=250,
                cost_est=0.0015,
                prompt="What are the symptoms of chest pain?",
                response="Chest pain can indicate various conditions...",
                latency_ms=1234.5,
                sensitive=False,
                trace_id=trace_id,
                session_id=session_id,
                user="bernard@example.com",
                role=UserRole.OWNER,
            )
            print("   ✅ Written to data/logs/llm/")

            # 4. Storage log
            print("4️⃣  Writing storage log (segment)...")
            writer.write_storage(
                file_path="storage/corpus.h5",
                sha256="abc123def456789...",
                segment_seconds=0.045,
                ready=True,
                trace_id=trace_id,
                session_id=session_id,
            )
            print("   ✅ Written to data/logs/storage/")

            print()
            print("✅ Demo logs written successfully!")
            print()
            print("Next steps:")
            print("   python3 backend/log_writer.py stats     # View statistics")
            print("   python3 backend/log_writer.py rotate    # Rotate logs")
            print("   python3 backend/log_writer.py manifest  # Create manifest")

        elif command == "stats":
            # Show statistics
            stats = writer.get_stats()

            print("📊 LOG STATISTICS")
            print()
            for channel, channel_stats in stats["log_stats"].items():
                print(f"{channel.upper()}:")
                print(f"   Files: {channel_stats['file_count']}")
                print(f"   Size: {channel_stats['total_size_mb']} MB")
                print(f"   Range: {channel_stats['oldest_date']} → {channel_stats['newest_date']}")
                print()

            manifest_stats = stats["manifest_stats"]
            print("MANIFESTS:")
            print(f"   Count: {manifest_stats['manifest_count']}")
            print(f"   Range: {manifest_stats['oldest_date']} → {manifest_stats['newest_date']}")
            print(f"   Total events: {manifest_stats['total_events']}")

        elif command == "rotate":
            # Rotate all logs
            print("🔄 Rotating logs...")
            results = writer.rotate_all()

            for channel, compressed in results.items():
                if compressed:
                    print(f"   ✅ {channel.value}: {compressed.name}")
                else:
                    print(f"   ⏭️  {channel.value}: No rotation needed")

        elif command == "cleanup":
            # Cleanup old logs
            print("🗑️  Cleaning up old logs...")
            results = writer.cleanup_all()

            for channel, count in results.items():
                if count > 0:
                    print(f"   ✅ {channel.value}: Deleted {count} old files")
                else:
                    print(f"   ✅ {channel.value}: No old files to delete")

        elif command == "manifest":
            # Create manifest
            date = sys.argv[2] if len(sys.argv) > 2 else None
            print("🔗 Creating manifest...")
            manifest = writer.create_manifest(date)

            print(f"   Date: {manifest['date']}")
            print(f"   Events: {manifest['event_count']}")
            print(f"   Access hash: {manifest['access_log_hash'][:16]}...")
            print(f"   Manifest hash: {manifest['manifest_hash'][:16]}...")

        elif command == "verify":
            # Verify manifests
            print("✅ Verifying manifest chain...")
            result = writer.verify_manifests()

            if result["valid"]:
                print(f"   ✅ VALID - All {result['manifests_checked']} manifests verified")
            else:
                print(f"   ❌ INVALID - Found {len(result['errors'])} errors:")
                for error in result["errors"]:
                    print(f"      [{error['date']}] {error['error']}")

        else:
            print(f"Unknown command: {command}")
            print()
            print("Available commands:")
            print("   demo     - Write sample logs")
            print("   stats    - Show statistics")
            print("   rotate   - Rotate logs")
            print("   cleanup  - Remove old logs")
            print("   manifest - Create daily manifest")
            print("   verify   - Verify manifest chain")

    else:
        print("Usage: python3 backend/log_writer.py [command]")
        print()
        print("Commands:")
        print("   demo              - Write sample logs to all channels")
        print("   stats             - Show log and manifest statistics")
        print("   rotate            - Rotate all logs")
        print("   cleanup           - Remove old logs per retention policy")
        print("   manifest [date]   - Create daily manifest (default: yesterday)")
        print("   verify            - Verify manifest chain integrity")
        print()
        print("Examples:")
        print("   python3 backend/log_writer.py demo")
        print("   python3 backend/log_writer.py stats")
        print("   python3 backend/log_writer.py manifest 2025-10-27")
        print("   python3 backend/log_writer.py verify")
