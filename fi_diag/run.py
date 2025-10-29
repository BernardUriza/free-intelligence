#!/usr/bin/env python3
"""
FI Diagnostic Runner

Card: FI-CORE-FEAT-005
Runs system health checks and alerts on failures.

Usage:
    python -m fi_diag.run [--dry-run] [--alert]
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import h5py
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("fi_diag")


@dataclass
class CheckResult:
    """Result of a health check"""

    check_name: str
    status: str  # OK, WARNING, CRITICAL
    message: str
    duration_ms: float
    timestamp: str
    details: Optional[dict[str, Any]] = None  # noqa: UP007


class DiagnosticRunner:
    """Runs diagnostic checks for Free Intelligence"""

    def __init__(self, config_path: str = "config/config.yml", dry_run: bool = False):
        self.config_path = Path(config_path)
        self.dry_run = dry_run
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> list[CheckResult]:
        """Run all diagnostic checks"""
        logger.info("Starting diagnostic checks...")

        checks = [
            self.check_corpus_integrity,
            self.check_api_latency,
            self.check_disk_space,
            self.check_docker_health,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
                self.results.append(result)
                logger.info(
                    f"[{result.check_name}] {result.status}: {result.message} ({result.duration_ms:.0f}ms)"
                )
            except Exception as e:
                logger.error(f"Check {check_fn.__name__} failed: {e}")
                self.results.append(
                    CheckResult(
                        check_name=check_fn.__name__,
                        status="CRITICAL",
                        message=f"Check failed: {str(e)}",
                        duration_ms=0,
                        timestamp=datetime.now().isoformat(),
                    )
                )

        return self.results

    def check_corpus_integrity(self) -> CheckResult:
        """Check HDF5 corpus file integrity"""
        start = time.time()
        check_name = "corpus_integrity"

        corpus_path = Path("storage/corpus.h5")

        if not corpus_path.exists():
            return CheckResult(
                check_name=check_name,
                status="WARNING",
                message="Corpus file not found (expected for fresh install)",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"path": str(corpus_path), "exists": False},
            )

        try:
            # Try to open corpus
            with h5py.File(corpus_path, "r") as corpus:
                # Count sessions
                session_count = 0
                if "/sessions" in corpus:
                    session_count = len(corpus["/sessions"].keys())

                # Check file size
                file_size_mb = corpus_path.stat().st_size / (1024 * 1024)

                # Verify structure (basic check)
                required_groups = []  # Empty for now, corpus may be empty
                missing_groups = [g for g in required_groups if g not in corpus]

                if missing_groups:
                    return CheckResult(
                        check_name=check_name,
                        status="WARNING",
                        message=f"Missing groups: {missing_groups}",
                        duration_ms=(time.time() - start) * 1000,
                        timestamp=datetime.now().isoformat(),
                        details={
                            "missing_groups": missing_groups,
                            "sessions": session_count,
                            "size_mb": file_size_mb,
                        },
                    )

                return CheckResult(
                    check_name=check_name,
                    status="OK",
                    message=f"Corpus healthy: {session_count} sessions, {file_size_mb:.1f}MB",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now().isoformat(),
                    details={"sessions": session_count, "size_mb": file_size_mb},
                )

        except Exception as e:
            return CheckResult(
                check_name=check_name,
                status="CRITICAL",
                message=f"Corpus corrupted or unreadable: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"error": str(e)},
            )

    def check_api_latency(self) -> CheckResult:
        """Check API response times"""
        start = time.time()
        check_name = "api_latency"

        apis = [
            {"name": "Timeline API", "url": "http://localhost:9002/health", "slo_ms": 100},
            {"name": "Verify API", "url": "http://localhost:9003/health", "slo_ms": 500},
        ]

        results = []
        failures = []

        for api in apis:
            try:
                api_start = time.time()
                resp = requests.get(api["url"], timeout=5)
                latency_ms = (time.time() - api_start) * 1000

                if resp.status_code != 200:
                    failures.append(f"{api['name']}: HTTP {resp.status_code}")
                elif latency_ms > api["slo_ms"]:
                    failures.append(f"{api['name']}: {latency_ms:.0f}ms > {api['slo_ms']}ms SLO")

                results.append(
                    {"name": api["name"], "latency_ms": latency_ms, "status_code": resp.status_code}
                )

            except requests.exceptions.RequestException as e:
                failures.append(f"{api['name']}: {str(e)}")
                results.append({"name": api["name"], "error": str(e)})

        if failures:
            return CheckResult(
                check_name=check_name,
                status="WARNING" if len(failures) < len(apis) else "CRITICAL",
                message=f"{len(failures)} API(s) unhealthy: {', '.join(failures)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"apis": results},
            )

        avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results)

        return CheckResult(
            check_name=check_name,
            status="OK",
            message=f"All APIs healthy (avg {avg_latency:.0f}ms)",
            duration_ms=(time.time() - start) * 1000,
            timestamp=datetime.now().isoformat(),
            details={"apis": results, "avg_latency_ms": avg_latency},
        )

    def check_disk_space(self) -> CheckResult:
        """Check available disk space"""
        start = time.time()
        check_name = "disk_space"

        storage_path = Path("storage")

        # Get disk usage (portable way)
        import shutil

        try:
            total, used, free = shutil.disk_usage(storage_path)

            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            used_pct = (used / total) * 100

            # Thresholds
            if used_pct > 90:
                status = "CRITICAL"
                message = f"Disk critically full: {used_pct:.1f}% used"
            elif used_pct > 75:
                status = "WARNING"
                message = f"Disk filling up: {used_pct:.1f}% used"
            else:
                status = "OK"
                message = f"Disk healthy: {used_pct:.1f}% used, {free_gb:.1f}GB free"

            return CheckResult(
                check_name=check_name,
                status=status,
                message=message,
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "used_pct": used_pct,
                },
            )

        except Exception as e:
            return CheckResult(
                check_name=check_name,
                status="CRITICAL",
                message=f"Disk check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"error": str(e)},
            )

    def check_docker_health(self) -> CheckResult:
        """Check Docker containers health (if applicable)"""
        start = time.time()
        check_name = "docker_health"

        try:
            import subprocess

            # Check if Docker is running
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return CheckResult(
                    check_name=check_name,
                    status="WARNING",
                    message="Docker not available (OK if not using containers)",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now().isoformat(),
                    details={"docker_available": False},
                )

            containers = result.stdout.strip().split("\n") if result.stdout.strip() else []

            if not containers:
                return CheckResult(
                    check_name=check_name,
                    status="OK",
                    message="No Docker containers running",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now().isoformat(),
                    details={"containers": []},
                )

            unhealthy = [c for c in containers if "unhealthy" in c.lower()]

            if unhealthy:
                return CheckResult(
                    check_name=check_name,
                    status="WARNING",
                    message=f"{len(unhealthy)} unhealthy container(s): {unhealthy}",
                    duration_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now().isoformat(),
                    details={"containers": containers, "unhealthy": unhealthy},
                )

            return CheckResult(
                check_name=check_name,
                status="OK",
                message=f"{len(containers)} container(s) healthy",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"containers": containers},
            )

        except FileNotFoundError:
            return CheckResult(
                check_name=check_name,
                status="WARNING",
                message="Docker not installed (OK if not using containers)",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"docker_available": False},
            )
        except Exception as e:
            return CheckResult(
                check_name=check_name,
                status="WARNING",
                message=f"Docker check failed: {str(e)}",
                duration_ms=(time.time() - start) * 1000,
                timestamp=datetime.now().isoformat(),
                details={"error": str(e)},
            )

    def generate_report(self) -> dict[str, Any]:
        """Generate diagnostic report"""
        critical_count = sum(1 for r in self.results if r.status == "CRITICAL")
        warning_count = sum(1 for r in self.results if r.status == "WARNING")
        ok_count = sum(1 for r in self.results if r.status == "OK")

        overall_status = "OK"
        if critical_count > 0:
            overall_status = "CRITICAL"
        elif warning_count > 0:
            overall_status = "WARNING"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_checks": len(self.results),
                "critical": critical_count,
                "warning": warning_count,
                "ok": ok_count,
            },
            "checks": [
                {
                    "name": r.check_name,
                    "status": r.status,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "timestamp": r.timestamp,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def send_alert(self, report: dict[str, Any]) -> None:
        """Send alert if critical issues found"""
        if self.dry_run:
            logger.info("[DRY RUN] Would send alert (alert system not implemented)")
            return

        # TODO: Implement AWS SNS integration (depends on FI-SEC-FEAT-002)
        logger.warning("Alert system not implemented yet (depends on FI-SEC-FEAT-002)")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Free Intelligence Diagnostic Runner")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no alerts)")
    parser.add_argument("--alert", action="store_true", help="Send alerts on failures")
    parser.add_argument("--output", type=str, help="Output JSON file path")

    args = parser.parse_args()

    runner = DiagnosticRunner(dry_run=args.dry_run)

    # Run checks
    runner.run_all_checks()

    # Generate report
    report = runner.generate_report()

    # Print summary
    print("\n" + "=" * 60)
    print(f"FI Diagnostic Report - {report['timestamp']}")
    print("=" * 60)
    print(f"Overall Status: {report['overall_status']}")
    print(
        f"Checks: {report['summary']['ok']} OK, {report['summary']['warning']} WARNING, {report['summary']['critical']} CRITICAL"
    )
    print("=" * 60)

    for check in report["checks"]:
        status_emoji = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌"}
        print(
            f"{status_emoji.get(check['status'], '?')} [{check['name']}] {check['status']}: {check['message']}"
        )

    print("=" * 60)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {output_path}")

    # Send alert if requested and critical issues found
    if args.alert and report["overall_status"] in ["WARNING", "CRITICAL"]:
        runner.send_alert(report)

    # Exit with error code if critical issues
    if report["overall_status"] == "CRITICAL":
        sys.exit(1)
    elif report["overall_status"] == "WARNING":
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
