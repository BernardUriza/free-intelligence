#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Log Rotation and Retention

Sistema de rotación y retención de logs NDJSON:
- Rotación: diaria o 50 MB (lo que ocurra primero)
- Compresión: gzip
- Retención: server/llm/storage 30 días, access 180 días (WORM lógico)

FI-CORE-FEAT-003
"""

import gzip
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from packages.fi_common.logging.logger_structured import ServiceChannel


class LogRotation:
    """
    Gestiona rotación y retención de archivos de log.

    Estructura de carpetas:
    /data/logs/
      server/    # req/resp API (metadatos)
      llm/       # prompts/respuestas truncadas + métricas
      storage/   # segmentación, SHA256, movimientos /ready
      access/    # login, cambios de rol, intentos fallidos (AUDIT)
      manifest/  # hash diario encadenado de access/*
    """

    def __init__(self, base_path: str = "data/logs"):
        """
        Initialize log rotation manager.

        Args:
            base_path: Base path para logs (default: data/logs)
        """
        self.base_path = Path(base_path)
        self.max_size_mb = 50
        self.retention_days = {
            ServiceChannel.SERVER: 30,
            ServiceChannel.LLM: 30,
            ServiceChannel.STORAGE: 30,
            ServiceChannel.ACCESS: 180,  # AUDIT logs - WORM lógico
        }

        # Crear estructura de carpetas
        self._ensure_directories()

    def _ensure_directories(self):
        """Crear estructura de carpetas si no existe."""
        for channel in ServiceChannel:
            channel_path = self.base_path / channel.value
            channel_path.mkdir(parents=True, exist_ok=True)

        # Manifest directory
        manifest_path = self.base_path / "manifest"
        manifest_path.mkdir(parents=True, exist_ok=True)

    def get_current_log_path(self, channel: ServiceChannel) -> Path:
        """
        Get current log file path for channel.

        Formato: YYYY-MM-DD.ndjson

        Args:
            channel: Service channel

        Returns:
            Path to current log file
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.base_path / channel.value / f"{today}.ndjson"

    def get_compressed_log_path(self, channel: ServiceChannel, date: str) -> Path:
        """
        Get compressed log file path.

        Formato: YYYY-MM-DD.ndjson.gz

        Args:
            channel: Service channel
            date: Date string (YYYY-MM-DD)

        Returns:
            Path to compressed log file
        """
        return self.base_path / channel.value / f"{date}.ndjson.gz"

    def should_rotate(self, channel: ServiceChannel) -> bool:
        """
        Check if log file should be rotated.

        Rotación cuando:
        - Archivo es de un día anterior (rotación diaria)
        - Tamaño >= 50 MB

        Args:
            channel: Service channel

        Returns:
            True if rotation needed
        """
        log_path = self.get_current_log_path(channel)

        if not log_path.exists():
            return False

        # Check if file is from previous day
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_date = log_path.stem  # YYYY-MM-DD

        if file_date != today:
            return True

        # Check file size
        file_size_mb = log_path.stat().st_size / (1024 * 1024)
        if file_size_mb >= self.max_size_mb:
            return True

        return False

    def rotate_log(self, channel: ServiceChannel) -> Optional[Path]:
        """
        Rotate log file (compress and create new).

        Args:
            channel: Service channel

        Returns:
            Path to compressed file, or None if no rotation needed
        """
        log_path = self.get_current_log_path(channel)

        if not log_path.exists():
            return None

        # Determine output filename
        file_date = log_path.stem
        compressed_path = self.get_compressed_log_path(channel, file_date)

        # If already compressed, add timestamp suffix
        if compressed_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
            compressed_path = self.base_path / channel.value / f"{file_date}-{timestamp}.ndjson.gz"

        # Compress log file
        with open(log_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove original
        log_path.unlink()

        return compressed_path

    def cleanup_old_logs(self, channel: ServiceChannel) -> list[Path]:
        """
        Remove logs older than retention period.

        Args:
            channel: Service channel

        Returns:
            List of deleted file paths
        """
        retention_days = self.retention_days[channel]
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        channel_path = self.base_path / channel.value
        deleted = []

        # Iterate over all .ndjson.gz files
        for log_file in channel_path.glob("*.ndjson.gz"):
            # Extract date from filename (YYYY-MM-DD.ndjson.gz)
            file_date_str = log_file.stem.split(".")[0].split("-")[:3]  # Handle YYYY-MM-DD-HHMMSS
            if len(file_date_str) != 3:
                continue

            try:
                file_date = datetime.strptime("-".join(file_date_str), "%Y-%m-%d")
                file_date = file_date.replace(tzinfo=UTC)

                if file_date < cutoff_date:
                    # WORM lógico para access: no eliminar, solo mover a archive
                    if channel == ServiceChannel.ACCESS:
                        archive_path = self.base_path / "manifest" / "archive"
                        archive_path.mkdir(exist_ok=True)
                        new_path = archive_path / log_file.name
                        shutil.move(str(log_file), str(new_path))
                        deleted.append(log_file)
                    else:
                        log_file.unlink()
                        deleted.append(log_file)
            except (ValueError, IndexError):
                continue

        return deleted

    def get_log_stats(self, channel: ServiceChannel) -> dict[str, Any]:
        """
        Get statistics for channel logs.

        Args:
            channel: Service channel

        Returns:
            Dict with stats: file_count, total_size_mb, oldest_date, newest_date
        """
        channel_path = self.base_path / channel.value
        log_files = list(channel_path.glob("*.ndjson*"))

        if not log_files:
            return {"file_count": 0, "total_size_mb": 0.0, "oldest_date": None, "newest_date": None}

        total_size = sum(f.stat().st_size for f in log_files)
        dates = []

        for log_file in log_files:
            file_date_str = log_file.stem.split(".")[0].split("-")[:3]
            if len(file_date_str) == 3:
                try:
                    file_date = datetime.strptime("-".join(file_date_str), "%Y-%m-%d")
                    dates.append(file_date)
                except ValueError:
                    continue

        return {
            "file_count": len(log_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_date": min(dates).strftime("%Y-%m-%d") if dates else None,
            "newest_date": max(dates).strftime("%Y-%m-%d") if dates else None,
        }

    def read_log_file(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Read log file (compressed or uncompressed).

        Args:
            file_path: Path to log file

        Returns:
            List of log events (dicts)
        """
        events = []

        if file_path.suffix == ".gz":
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        else:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return events


# ============================================================================
# CLI Demo
# ============================================================================

if __name__ == "__main__":
    import sys

    print("🔄 FREE INTELLIGENCE - LOG ROTATION DEMO")
    print("=" * 60)
    print()

    rotation = LogRotation(base_path="data/logs")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            # Show stats for all channels
            for channel in ServiceChannel:
                stats = rotation.get_log_stats(channel)
                print(f"📊 {channel.value.upper()} Stats:")
                print(f"   Files: {stats['file_count']}")
                print(f"   Size: {stats['total_size_mb']} MB")
                print(f"   Oldest: {stats['oldest_date']}")
                print(f"   Newest: {stats['newest_date']}")
                print()

        elif command == "rotate":
            # Rotate all channels
            for channel in ServiceChannel:
                if rotation.should_rotate(channel):
                    compressed = rotation.rotate_log(channel)
                    if compressed:
                        print(f"✅ Rotated {channel.value}: {compressed.name}")
                else:
                    print(f"⏭️  {channel.value}: No rotation needed")

        elif command == "cleanup":
            # Cleanup old logs
            for channel in ServiceChannel:
                deleted = rotation.cleanup_old_logs(channel)
                if deleted:
                    print(f"🗑️  {channel.value}: Deleted {len(deleted)} old files")
                else:
                    print(f"✅ {channel.value}: No old files to delete")

        else:
            print(f"Unknown command: {command}")
            print("Usage: python3 log_rotation.py [stats|rotate|cleanup]")

    else:
        # Demo: show current log paths
        print("Current log paths:")
        for channel in ServiceChannel:
            log_path = rotation.get_current_log_path(channel)
            print(f"   {channel.value}: {log_path}")
        print()

        print("Retention policies:")
        for channel in ServiceChannel:
            days = rotation.retention_days[channel]
            worm = " (WORM lógico)" if channel == ServiceChannel.ACCESS else ""
            print(f"   {channel.value}: {days} días{worm}")
        print()

        print("Usage:")
        print("   python3 log_rotation.py stats    # Show statistics")
        print("   python3 log_rotation.py rotate   # Rotate logs")
        print("   python3 log_rotation.py cleanup  # Remove old logs")
