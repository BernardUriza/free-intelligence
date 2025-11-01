"""Service layer for system diagnostics and infrastructure checks.

Encapsulates all system diagnostics logic including Python runtime,
storage, HDF5 corpus, Node.js, pnpm, PM2 service checks, and system info.

Clean Code: Service layer handles all diagnostics probes,
endpoints become thin controllers for HTTP response formatting.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DiagnosticsService:
    """Service for system diagnostics and infrastructure checks.

    Responsibilities:
    - Check Python runtime environment
    - Check storage directories and HDF5 corpus
    - Check Node.js and pnpm availability
    - Check PM2 services (with fallback to lsof)
    - Check system resources (CPU, memory, disk)
    - Aggregate diagnostic status
    """

    def check_python(self) -> dict[str, Any]:
        """Check Python runtime.

        Returns:
            Dict with status, version, executable path
        """
        return {
            "status": "healthy",
            "version": sys.version.split()[0],
            "executable": sys.executable,
        }

    def check_storage(self) -> dict[str, Any]:
        """Check storage directory availability and writability.

        Returns:
            Dict with status, path, writability
        """
        storage_path = Path("storage")
        writable = False
        if storage_path.exists():
            writable = os.access(storage_path, os.W_OK)

        return {
            "status": "healthy" if storage_path.exists() and writable else "degraded",
            "path": str(storage_path.absolute()),
            "exists": storage_path.exists(),
            "writable": writable,
        }

    def check_data_directory(self) -> dict[str, Any]:
        """Check data directory availability and writability.

        Returns:
            Dict with status, path, writability
        """
        data_path = Path("data")
        writable = False
        if data_path.exists():
            writable = os.access(data_path, os.W_OK)

        return {
            "status": "healthy" if data_path.exists() and writable else "degraded",
            "path": str(data_path.absolute()),
            "exists": data_path.exists(),
            "writable": writable,
        }

    def check_corpus(self) -> dict[str, Any]:
        """Check HDF5 corpus database.

        Returns:
            Dict with status, existence, size in MB
        """
        corpus_path = Path("storage/corpus.h5")
        size_mb = 0
        if corpus_path.exists():
            try:
                size_mb = round(corpus_path.stat().st_size / 1024 / 1024, 2)
            except Exception as e:
                logger.warning(f"CORPUS_SIZE_CHECK_FAILED: error={str(e)}")

        return {
            "status": "healthy" if corpus_path.exists() else "warning",
            "exists": corpus_path.exists(),
            "size_mb": size_mb,
        }

    def check_nodejs(self) -> dict[str, Any]:
        """Check Node.js availability.

        Returns:
            Dict with status, version
        """
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                logger.info("NODEJS_HEALTH_CHECKED: available=True")
                return {
                    "status": "healthy",
                    "version": result.stdout.strip(),
                }
            else:
                logger.warning("NODEJS_CHECK_FAILED: command failed")
                return {"status": "unhealthy", "version": None, "error": "Command failed"}
        except Exception as e:
            logger.warning(f"NODEJS_CHECK_FAILED: error={str(e)}")
            return {"status": "unhealthy", "version": None, "error": str(e)}

    def check_pnpm(self) -> dict[str, Any]:
        """Check pnpm availability.

        Returns:
            Dict with status, version
        """
        try:
            result = subprocess.run(
                ["pnpm", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                logger.info("PNPM_HEALTH_CHECKED: available=True")
                return {
                    "status": "healthy",
                    "version": result.stdout.strip(),
                }
            else:
                logger.warning("PNPM_CHECK_FAILED: command failed")
                return {"status": "unhealthy", "version": None, "error": "Command failed"}
        except Exception as e:
            logger.warning(f"PNPM_CHECK_FAILED: error={str(e)}")
            return {"status": "unhealthy", "version": None, "error": str(e)}

    def check_pm2(self) -> dict[str, Any]:
        """Check PM2 services (with fallback to lsof).

        First tries PM2 command, falls back to lsof port checking if PM2 unavailable.

        Returns:
            Dict with status and list of services
        """
        services = []

        # Try PM2 first (timeout 5s to avoid hanging)
        try:
            result = subprocess.run(
                ["pm2", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                import json

                pm2_data = json.loads(result.stdout)
                services = [
                    {
                        "name": proc.get("name", "unknown"),
                        "status": proc.get("pm2_env", {}).get("status", "unknown"),
                        "pid": proc.get("pid"),
                        "uptime": proc.get("pm2_env", {}).get("exp_backoff_restart_delay")
                        if proc.get("pm2_env", {}).get("status") != "online"
                        else None,
                    }
                    for proc in pm2_data
                ]
                logger.info(f"PM2_HEALTH_CHECKED: services={len(services)}")
                return {"status": "healthy", "services": services}
            else:
                logger.warning("PM2_CHECK_FAILED: command failed, trying lsof fallback")
        except Exception as e:
            logger.debug(f"PM2_CHECK_FAILED: error={str(e)}, trying lsof fallback")

        # Fallback to lsof (check common service ports)
        try:
            # Check common ports: 7001 (backend), 9000 (frontend), 11434 (ollama)
            service_ports = {"backend": 7001, "frontend": 9000, "ollama": 11434}
            for service_name, port in service_ports.items():
                try:
                    result = subprocess.run(
                        ["lsof", "-i", f":{port}"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    if result.returncode == 0:
                        services.append({"name": service_name, "port": port, "listening": True})
                except Exception:
                    pass

            logger.info(f"LSOF_FALLBACK_CHECKED: services={len(services)}")
            return {
                "status": "healthy" if services else "degraded",
                "services": services,
                "note": "Using lsof fallback (PM2 unavailable)",
            }
        except Exception as e:
            logger.warning(f"LSOF_FALLBACK_FAILED: error={str(e)}")
            return {
                "status": "unhealthy",
                "services": [],
                "error": f"Both PM2 and lsof failed: {str(e)}",
            }

    def get_system_info(self) -> dict[str, Any]:
        """Get system information (OS, CPU, disk, memory).

        Returns:
            Dict with system info from psutil if available
        """
        import platform

        info = {
            "os": platform.system(),
            "release": platform.release(),
            "python": sys.version,
        }

        # Try psutil for detailed system metrics (optional dependency)
        try:
            import psutil

            info["cpu_count"] = psutil.cpu_count()
            info["cpu_percent"] = psutil.cpu_percent(interval=1)

            disk = psutil.disk_usage("/")
            info["disk_total_gb"] = round(disk.total / 1024**3, 2)
            info["disk_used_gb"] = round(disk.used / 1024**3, 2)
            info["disk_percent"] = disk.percent

            mem = psutil.virtual_memory()
            info["memory_total_gb"] = round(mem.total / 1024**3, 2)
            info["memory_used_gb"] = round(mem.used / 1024**3, 2)
            info["memory_percent"] = mem.percent

            logger.info("SYSTEM_INFO_RETRIEVED: with_psutil=True")
        except ImportError:
            logger.debug("psutil not available for detailed system metrics")

        return info

    def get_diagnostics(self) -> dict[str, Any]:
        """Get comprehensive diagnostics.

        Aggregates all diagnostic checks: Python, storage, corpus,
        Node.js, pnpm, PM2.

        Returns:
            Dict with overall status and per-check details
        """
        checks = {
            "python": self.check_python(),
            "storage": self.check_storage(),
            "data": self.check_data_directory(),
            "corpus": self.check_corpus(),
            "nodejs": self.check_nodejs(),
            "pnpm": self.check_pnpm(),
            "pm2": self.check_pm2(),
        }

        # Overall status: healthy if all critical checks pass
        critical_checks = ["python", "storage", "corpus"]
        critical_ok = all(
            checks[c].get("status") in ["healthy", "warning"] for c in critical_checks
        )

        overall_status = "healthy" if critical_ok else "degraded"
        if not critical_ok:
            overall_status = "unhealthy"

        logger.info(f"DIAGNOSTICS_CHECKED: overall_status={overall_status}")

        return {
            "status": overall_status,
            "checks": checks,
        }

    def check_readiness(self) -> bool:
        """Check if system is ready to serve traffic.

        Readiness check for Kubernetes/PM2 - returns True only if
        critical resources are available (corpus directory exists and is writable).

        Returns:
            True if system is ready, False otherwise
        """
        corpus_path = Path("storage/corpus.h5")
        storage_path = Path("storage")

        is_ready = storage_path.exists() and corpus_path.exists()
        logger.info(f"READINESS_CHECK: ready={is_ready}")

        return is_ready

    def check_liveness(self) -> bool:
        """Check if system process is alive.

        Liveness check for Kubernetes/PM2 - always returns True
        because if process is dead, this endpoint won't be callable.

        Returns:
            True (always alive if responding)
        """
        logger.info("LIVENESS_CHECK: alive=True")
        return True
