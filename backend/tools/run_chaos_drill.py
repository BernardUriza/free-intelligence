#!/usr/bin/env python3
"""
Chaos Drill Runner

Card: FI-RELIABILITY-STR-001, FI-RELIABILITY-IMPL-002
Runs chaos engineering drills based on policies/error_budgets.yml

Usage:
    python scripts/run_chaos_drill.py network_partition --dry-run
    python scripts/run_chaos_drill.py corpus_file_lock --execute --concurrency 10
    python scripts/run_chaos_drill.py network_partition --port 7001 --duration 20 --yes
"""

import yaml

import argparse
import fcntl
import json
import logging
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("chaos_drill")


class ChaosDrill:
    """Base class for chaos drills"""

    def __init__(self, config: Dict[str, Any], dry_run: bool = True):
        self.config = config
        self.dry_run = dry_run
        self.results: list[dict[str, Any]] = []

    def pre_check(self) -> bool:
        """Pre-flight checks before drill"""
        raise NotImplementedError

    def inject_chaos(self) -> None:
        """Inject chaos into the system"""
        raise NotImplementedError

    def observe(self) -> None:
        """Observe system behavior during chaos"""
        raise NotImplementedError

    def restore(self) -> None:
        """Restore system to normal state"""
        raise NotImplementedError

    def validate(self) -> dict[str, Any]:
        """Validate success criteria"""
        raise NotImplementedError

    def run(self) -> dict[str, Any]:
        """Run the full drill"""
        logger.info(f"Starting chaos drill: {self.config['objective']}")

        if self.dry_run:
            logger.warning("[DRY RUN] No actual chaos will be injected")

        # Pre-check
        if not self.pre_check():
            return {"status": "FAILED", "reason": "Pre-check failed"}

        start_time = time.time()

        try:
            # Phase 1: Inject chaos
            logger.info("Phase 1: Injecting chaos...")
            self.inject_chaos()

            # Phase 2: Observe
            logger.info("Phase 2: Observing system behavior...")
            self.observe()

            # Phase 3: Restore
            logger.info("Phase 3: Restoring system...")
            self.restore()

            # Phase 4: Validate
            logger.info("Phase 4: Validating success criteria...")
            validation = self.validate()

            duration_sec = time.time() - start_time

            return {
                "status": "SUCCESS" if validation["passed"] else "FAILED",
                "duration_sec": duration_sec,
                "validation": validation,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Drill failed with exception: {e}")
            self.restore()  # Emergency restore
            return {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


class NetworkPartitionDrill(ChaosDrill):
    """Network partition drill (Linux iptables, macOS pfctl/app-mock)"""

    def __init__(
        self, config: Dict[str, Any], dry_run: bool = True, port: int = 7001, duration: int = 20
    ):
        super().__init__(config, dry_run)
        self.port = port
        self.duration = duration
        self.platform_name = platform.system()
        self.mode = None  # Will be set in pre_check: "linux-iptables", "darwin-pf", "app-mock"
        self.errors: List[str] = []
        self.pf_enabled_by_us = False

    def pre_check(self) -> bool:
        """Detect platform and check available tools"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Platform: {self.platform_name}")
            logger.info("[DRY RUN] Would check available chaos methods")
            self.mode = "dry-run"
            return True

        logger.info(f"Platform detected: {self.platform_name}")

        if self.platform_name == "Linux":
            # Check for iptables
            try:
                result = subprocess.run(["which", "iptables"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.mode = "linux-iptables"
                    logger.info("Mode: linux-iptables")
                    return True
            except Exception as e:
                logger.error(f"iptables check failed: {e}")

        elif self.platform_name == "Darwin":
            # Check pfctl
            try:
                result = subprocess.run(["pfctl", "-s", "info"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    # Check if lo0 is skipped (common default)
                    skip_check = subprocess.run(
                        ["grep", "-q", "skip on lo0", "/etc/pf.conf"], capture_output=True
                    )
                    if skip_check.returncode == 0:
                        logger.warning("pf.conf has 'skip on lo0' - localhost filtering disabled")
                        logger.info("Falling back to app-mock mode")
                        self.mode = "app-mock"
                    else:
                        self.mode = "darwin-pf"
                        logger.info("Mode: darwin-pf (packet filter)")
                    return True
            except Exception as e:
                logger.warning(f"pfctl check failed: {e}, using app-mock")
                self.mode = "app-mock"
                return True

        # Fallback to app-mock for any platform
        logger.warning(f"No network chaos tools available on {self.platform_name}")
        self.mode = "app-mock"
        logger.info("Mode: app-mock (environment variable flag)")
        return True

    def inject_chaos(self) -> None:
        """Inject network partition based on platform"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute chaos injection mode={self.mode}")
            logger.info(f"[DRY RUN] Target port: {self.port}, duration: {self.duration}s")
            return

        if self.mode == "linux-iptables":
            self._inject_linux_iptables()
        elif self.mode == "darwin-pf":
            self._inject_darwin_pf()
        elif self.mode == "app-mock":
            self._inject_app_mock()
        else:
            raise RuntimeError(f"Unknown mode: {self.mode}")

    def _inject_linux_iptables(self) -> None:
        """Linux: Block port with iptables"""
        logger.info(f"Injecting iptables rule to block port {self.port}")
        try:
            subprocess.run(
                [
                    "sudo",
                    "iptables",
                    "-I",
                    "OUTPUT",
                    "-p",
                    "tcp",
                    "--dport",
                    str(self.port),
                    "-j",
                    "DROP",
                ],
                check=True,
                timeout=10,
            )
            logger.info(f"✅ Port {self.port} blocked via iptables")
        except Exception as e:
            self.errors.append(f"iptables inject failed: {e}")
            logger.error(f"Failed to inject iptables rule: {e}")

    def _inject_darwin_pf(self) -> None:
        """macOS: Block port with pfctl"""
        logger.info(f"Injecting pf rule to block port {self.port}")
        try:
            # Enable pf if not already enabled
            pf_status = subprocess.run(["pfctl", "-s", "info"], capture_output=True)
            if b"Status: Disabled" in pf_status.stdout:
                subprocess.run(["sudo", "pfctl", "-E"], check=True)
                self.pf_enabled_by_us = True
                logger.info("Enabled pf (packet filter)")

            # Add blocking rule to anchor
            rule = f"block drop quick proto tcp from any to any port {self.port}"
            subprocess.run(
                ["sudo", "pfctl", "-a", "fi/chaos", "-f", "-"],
                input=rule.encode(),
                check=True,
                timeout=10,
            )
            logger.info(f"✅ Port {self.port} blocked via pf")
        except Exception as e:
            self.errors.append(f"pfctl inject failed: {e}")
            logger.error(f"Failed to inject pf rule: {e}")

    def _inject_app_mock(self) -> None:
        """App-level mock: Set environment variable"""
        logger.info("Injecting app-mock (environment variable)")
        os.environ["FI_CHAOS_BLOCK_BACKEND"] = "1"
        os.environ["FI_CHAOS_BLOCK_PORT"] = str(self.port)
        logger.warning("⚠️ App-mock mode: Application must check FI_CHAOS_BLOCK_BACKEND")
        logger.info("✅ Environment variables set")

    def observe(self) -> None:
        """Observe system behavior during partition"""
        if self.dry_run:
            logger.info("[DRY RUN] Would monitor system during partition")
            time.sleep(2)
            return

        logger.info(f"Observing system for {self.duration}s...")

        # Test that port is actually blocked
        if self.mode != "app-mock":
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("127.0.0.1", self.port))
                sock.close()

                if result == 0:
                    logger.warning(f"⚠️ Port {self.port} still accessible (block may have failed)")
                else:
                    logger.info(f"✅ Port {self.port} blocked successfully")
            except Exception as e:
                logger.warning(f"Port check failed: {e}")

        time.sleep(self.duration)

    def restore(self) -> None:
        """Restore network connectivity"""
        if self.dry_run:
            logger.info("[DRY RUN] Would restore network connectivity")
            return

        if self.mode == "linux-iptables":
            self._restore_linux_iptables()
        elif self.mode == "darwin-pf":
            self._restore_darwin_pf()
        elif self.mode == "app-mock":
            self._restore_app_mock()

    def _restore_linux_iptables(self) -> None:
        """Remove iptables rule"""
        logger.info("Removing iptables rule...")
        try:
            subprocess.run(
                [
                    "sudo",
                    "iptables",
                    "-D",
                    "OUTPUT",
                    "-p",
                    "tcp",
                    "--dport",
                    str(self.port),
                    "-j",
                    "DROP",
                ],
                check=True,
                timeout=10,
            )
            logger.info("✅ iptables rule removed")
        except Exception as e:
            self.errors.append(f"iptables restore failed: {e}")
            logger.error(f"Failed to remove iptables rule: {e}")

    def _restore_darwin_pf(self) -> None:
        """Remove pf rule and disable if we enabled it"""
        logger.info("Removing pf rule...")
        try:
            subprocess.run(["sudo", "pfctl", "-a", "fi/chaos", "-F", "all"], check=True)
            logger.info("✅ pf rule removed")

            if self.pf_enabled_by_us:
                subprocess.run(["sudo", "pfctl", "-d"], check=True)
                logger.info("Disabled pf (was enabled by drill)")
        except Exception as e:
            self.errors.append(f"pfctl restore failed: {e}")
            logger.error(f"Failed to remove pf rule: {e}")

    def _restore_app_mock(self) -> None:
        """Unset environment variables"""
        logger.info("Removing app-mock environment variables...")
        os.environ.pop("FI_CHAOS_BLOCK_BACKEND", None)
        os.environ.pop("FI_CHAOS_BLOCK_PORT", None)
        logger.info("✅ Environment variables removed")

    def validate(self) -> dict[str, Any]:
        """Validate drill execution"""
        if self.dry_run:
            return {
                "passed": True,
                "mode": self.mode,
                "target_port": self.port,
                "duration_sec": self.duration,
                "details": "Dry run validation",
            }

        # Test that port is accessible again
        accessible = False
        if self.mode != "app-mock":
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("127.0.0.1", self.port))
                sock.close()
                accessible = result == 0
            except:
                pass

        success = len(self.errors) == 0
        if self.mode != "app-mock" and not accessible:
            self.errors.append("Port still not accessible after restore")
            success = False

        return {
            "passed": success,
            "mode": self.mode,
            "target_port": self.port,
            "duration_sec": self.duration,
            "platform": self.platform_name,
            "port_accessible_after_restore": accessible if self.mode != "app-mock" else None,
            "errors": self.errors,
            "details": f"Executed {self.mode} on {self.platform_name}, {len(self.errors)} errors",
        }


class CorpusFileLockDrill(ChaosDrill):
    """Corpus file lock drill (concurrent access)"""

    def __init__(
        self,
        config: Dict[str, Any],
        dry_run: bool = True,
        file_path: str = "storage/corpus.h5",
        concurrency: int = 10,
        duration: int = 20,
        join_grace: Optional[int] = None,
    ):
        super().__init__(config, dry_run)
        self.file_path = file_path
        self.concurrency = concurrency
        self.duration = duration
        # Calculate realistic join timeout for serial queue: ceil(duration * concurrency * 1.2) + 5
        import math

        self.join_grace = (
            join_grace if join_grace is not None else math.ceil(duration * concurrency * 1.2) + 5
        )
        self.processes: list[mp.Process] = []
        self.pids: list[int] = []
        self.errors: List[str] = []
        self.crash_count = 0
        self.join_timeout_count = 0

    def pre_check(self) -> bool:
        """Check if corpus file exists"""
        corpus_path = Path(self.file_path)
        exists = corpus_path.exists()

        if not exists and not self.dry_run:
            logger.error(f"Corpus file not found: {self.file_path}")
            return False

        if not exists:
            logger.warning("Corpus file not found (OK for dry run)")

        return True

    @staticmethod
    def _hold_lock(file_path: str, duration: int, proc_id: int) -> None:
        """Hold exclusive lock on file for duration seconds"""
        try:
            logger.info(f"[Process {proc_id}] Attempting to acquire lock on {file_path}")
            with open(file_path, "a+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                logger.info(f"[Process {proc_id}] Lock acquired, holding for {duration}s")
                time.sleep(duration)
                fcntl.flock(f, fcntl.LOCK_UN)
                logger.info(f"[Process {proc_id}] Lock released")
        except Exception as e:
            logger.error(f"[Process {proc_id}] Error: {e}")
            sys.exit(1)

    def inject_chaos(self) -> None:
        """Spawn concurrent processes with file locks"""
        if self.dry_run:
            logger.info("[DRY RUN] Would execute:")
            logger.info(f"  - Spawn {self.concurrency} concurrent processes")
            logger.info(f"  - Each holds LOCK_EX on {self.file_path} for {self.duration}s")
            return

        logger.info(f"Spawning {self.concurrency} concurrent processes...")
        for i in range(self.concurrency):
            p = mp.Process(target=self._hold_lock, args=(self.file_path, self.duration, i))
            p.start()
            self.processes.append(p)
            self.pids.append(p.pid)
            logger.info(f"Started process {i} (PID: {p.pid})")

    def observe(self) -> None:
        """Observe process execution and lock contention"""
        if self.dry_run:
            logger.info("[DRY RUN] Would monitor:")
            logger.info("  - Lock wait time")
            logger.info("  - Retry attempts")
            logger.info("  - Error rate")
            logger.info(
                f"  - join_grace={self.join_grace}s (calculated from concurrency*duration*1.2)"
            )
            time.sleep(2)
            return

        queueing_estimate = self.duration * self.concurrency
        logger.info(
            f"Waiting for {len(self.processes)} processes (join_grace={self.join_grace}s, queue estimate={queueing_estimate}s)..."
        )

        for i, p in enumerate(self.processes):
            p.join(timeout=self.join_grace)
            if p.is_alive():
                logger.warning(
                    f"Process {i} (PID {p.pid}) still alive after join_grace={self.join_grace}s"
                )
                self.join_timeout_count += 1
                # Don't add to errors - this is expected behavior for serial queue
            elif p.exitcode != 0:
                logger.error(f"Process {i} (PID {p.pid}) CRASHED with exit code {p.exitcode}")
                self.errors.append(f"Process {i} CRASH (exit {p.exitcode})")
                self.crash_count += 1
            else:
                logger.info(f"Process {i} (PID {p.pid}) completed successfully")

    def restore(self) -> None:
        """Terminate any remaining processes"""
        if self.dry_run:
            logger.info("[DRY RUN] Would execute:")
            logger.info("  - Terminate all test processes")
            return

        alive_count = sum(1 for p in self.processes if p.is_alive())
        if alive_count > 0:
            logger.warning(f"Terminating {alive_count} remaining processes")
            for p in self.processes:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=5)
                    if p.is_alive():
                        p.kill()
        else:
            logger.info("All processes completed, no cleanup needed")

    def validate(self) -> dict[str, Any]:
        """Validate drill execution with robust status logic"""
        if self.dry_run:
            return {
                "passed": True,
                "status": "SUCCESS",
                "criteria": self.config.get("success_criteria", []),
                "details": "Dry run validation",
            }

        all_dead = all(not p.is_alive() for p in self.processes)

        # Status logic:
        # SUCCESS: 0 crashes, locks released (even if join timeouts due to serial queue)
        # PARTIAL: join timeouts but 0 crashes
        # FAILED: any crashes
        if self.crash_count == 0 and all_dead:
            status = "SUCCESS"
            passed = True
        elif self.crash_count == 0 and self.join_timeout_count > 0:
            status = "PARTIAL"
            passed = True  # Still acceptable
        else:
            status = "FAILED"
            passed = False

        queueing_estimate = self.duration * self.concurrency

        return {
            "passed": passed,
            "status": status,
            "concurrency": self.concurrency,
            "duration": self.duration,
            "join_grace": self.join_grace,
            "pids": self.pids,
            "crash_count": self.crash_count,
            "join_timeout_count": self.join_timeout_count,
            "queueing_time_estimate": queueing_estimate,
            "join_timeout_applied": self.join_grace,
            "errors": self.errors,
            "all_completed": all_dead,
            "details": f"{len(self.pids)} processes spawned, {self.crash_count} crashes, {self.join_timeout_count} join timeouts",
        }


class LLMTimeoutStormDrill(ChaosDrill):
    """LLM timeout storm drill (app-mock or HTTP hammering)"""

    def __init__(
        self,
        config: Dict[str, Any],
        dry_run: bool = True,
        mode: str = "app-mock",
        duration: int = 20,
        concurrency: int = 10,
        timeout_ms: int = 1500,
        rps: int = 5,
    ):
        super().__init__(config, dry_run)
        self.mode = mode  # "app-mock" or "http"
        self.duration = duration
        self.concurrency = concurrency
        self.timeout_ms = timeout_ms
        self.rps = rps
        self.timeout_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.latencies: list[float] = []

    def pre_check(self) -> bool:
        """Check if target endpoint is available (for HTTP mode)"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Mode: {self.mode}")
            return True

        if self.mode == "http":
            # Check if LLM endpoint is accessible
            try:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("127.0.0.1", 11434))
                sock.close()
                if result != 0:
                    logger.warning(
                        "LLM endpoint (localhost:11434) not accessible, using app-mock fallback"
                    )
                    self.mode = "app-mock"
            except Exception as e:
                logger.warning(f"HTTP check failed: {e}, using app-mock")
                self.mode = "app-mock"

        logger.info(f"Mode: {self.mode}")
        return True

    def inject_chaos(self) -> None:
        """Inject timeout storm"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would inject {self.mode} timeout storm")
            logger.info(
                f"[DRY RUN] Duration={self.duration}s, concurrency={self.concurrency}, timeout={self.timeout_ms}ms, rps={self.rps}"
            )
            return

        if self.mode == "app-mock":
            self._inject_app_mock()
        elif self.mode == "http":
            self._inject_http_storm()

    def _inject_app_mock(self) -> None:
        """App-mock: Set environment variables"""
        logger.info("Injecting app-mock LLM timeout storm")
        os.environ["FI_CHAOS_LLM_DELAY_MS"] = str(self.timeout_ms)
        os.environ["FI_CHAOS_LLM_TIMEOUT_RATE"] = "0.3"  # 30% timeout rate
        logger.info(f"✅ Environment variables set: DELAY_MS={self.timeout_ms}, TIMEOUT_RATE=0.3")

    def _inject_http_storm(self) -> None:
        """HTTP: Hammer LLM endpoint with concurrent requests"""
        import requests

        from concurrent.futures import ThreadPoolExecutor, as_completed

        logger.info(f"Starting HTTP storm: {self.concurrency} workers, {self.rps} RPS")

        def _make_request():
            try:
                start = time.time()
                resp = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3.2:1b", "prompt": "test", "stream": False},
                    timeout=self.timeout_ms / 1000.0,
                )
                latency_ms = (time.time() - start) * 1000
                self.latencies.append(latency_ms)
                if resp.status_code == 200:
                    self.success_count += 1
                return "success"
            except requests.Timeout:
                self.timeout_count += 1
                return "timeout"
            except Exception as e:
                logger.debug(f"Request error: {e}")
                return "error"

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            requests_per_second = self.rps
            total_requests = requests_per_second * self.duration
            interval = 1.0 / requests_per_second

            futures = []
            for _i in range(total_requests):
                futures.append(executor.submit(_make_request))
                time.sleep(interval)

            # Wait for all to complete
            for future in as_completed(futures):
                self.total_requests += 1
                future.result()

    def observe(self) -> None:
        """Observe system behavior during storm"""
        if self.dry_run:
            logger.info("[DRY RUN] Would monitor timeout rates and latencies")
            time.sleep(2)
            return

        if self.mode == "app-mock":
            logger.info(f"Observing app-mock storm for {self.duration}s...")
            time.sleep(self.duration)
        else:
            # HTTP mode: observation happens during inject
            pass

    def restore(self) -> None:
        """Restore normal operation"""
        if self.dry_run:
            logger.info("[DRY RUN] Would restore normal LLM operation")
            return

        if self.mode == "app-mock":
            logger.info("Removing app-mock environment variables...")
            os.environ.pop("FI_CHAOS_LLM_DELAY_MS", None)
            os.environ.pop("FI_CHAOS_LLM_TIMEOUT_RATE", None)
            logger.info("✅ Environment variables removed")

    def validate(self) -> dict[str, Any]:
        """Validate drill results"""
        if self.dry_run:
            return {"passed": True, "mode": self.mode, "details": "Dry run validation"}

        if self.mode == "app-mock":
            return {
                "passed": True,
                "mode": self.mode,
                "timeout_ms": self.timeout_ms,
                "duration": self.duration,
                "details": "App-mock storm completed (check application logs for degradation)",
            }

        # HTTP mode: calculate metrics
        timeout_pct = (
            (self.timeout_count / self.total_requests * 100) if self.total_requests > 0 else 0
        )
        p95_latency = (
            sorted(self.latencies)[int(len(self.latencies) * 0.95)] if self.latencies else 0
        )

        return {
            "passed": timeout_pct > 0,  # We expect some timeouts
            "mode": self.mode,
            "timeout_ms": self.timeout_ms,
            "duration": self.duration,
            "concurrency": self.concurrency,
            "rps": self.rps,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "timeout_count": self.timeout_count,
            "timeout_pct": round(timeout_pct, 2),
            "p95_latency_ms": round(p95_latency, 2) if p95_latency else None,
            "details": f"{self.total_requests} requests, {timeout_pct:.1f}% timeouts, p95={p95_latency:.0f}ms",
        }


class DiskFullDrill(ChaosDrill):
    """Disk full drill (safe, reversible)"""

    def __init__(
        self,
        config: Dict[str, Any],
        dry_run: bool = True,
        path: str = "/tmp/fi-chaos-disk",
        fill_until_pct: int = 95,
        max_gb: float = 2.0,
        duration: int = 20,
    ):
        super().__init__(config, dry_run)
        self.path = Path(path)
        self.fill_until_pct = fill_until_pct
        self.max_gb = max_gb
        self.duration = duration
        self.filled_gb = 0.0
        self.created_files: list[Path] = []
        self.backend_write_error = False

    def pre_check(self) -> bool:
        """Check if path is safe for chaos injection"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would check path safety: {self.path}")
            return True

        # Safety: only allow /tmp or test paths
        safe_paths = [
            "/tmp",
            "/var/tmp",
            "/private/tmp",
            "/private/var/tmp",
        ]  # macOS uses /private/tmp
        path_str = str(self.path.resolve())

        is_safe = any(path_str.startswith(p) for p in safe_paths)
        if not is_safe:
            logger.error(f"Unsafe path: {path_str} (must start with one of {safe_paths})")
            return False

        # Create directory if needed
        self.path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Path is safe: {self.path}")
        return True

    def inject_chaos(self) -> None:
        """Fill disk to specified percentage or max GB"""
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would fill {self.path} to {self.fill_until_pct}% or {self.max_gb}GB max"
            )
            return

        logger.info(
            f"Filling disk at {self.path} (target: {self.fill_until_pct}%, max: {self.max_gb}GB)"
        )

        chunk_size_mb = 128
        chunk_bytes = chunk_size_mb * 1024 * 1024
        max_bytes = int(self.max_gb * 1024 * 1024 * 1024)

        file_counter = 0
        while self.filled_gb < self.max_gb:
            file_path = self.path / f"fi_chaos_{file_counter:04d}.bin"

            try:
                with open(file_path, "wb") as f:
                    f.write(b"\x00" * chunk_bytes)
                    f.flush()
                    os.fsync(f.fileno())

                self.created_files.append(file_path)
                self.filled_gb += chunk_size_mb / 1024.0
                file_counter += 1

                logger.info(f"Created {file_path.name} ({self.filled_gb:.2f}GB filled)")

                # Check if we should stop
                if len(self.created_files) * chunk_bytes >= max_bytes:
                    logger.info(f"Reached max_gb={self.max_gb}GB limit")
                    break

            except OSError as e:
                logger.warning(f"Disk full encountered: {e}")
                break

        logger.info(f"✅ Filled {self.filled_gb:.2f}GB ({len(self.created_files)} files)")

    def observe(self) -> None:
        """Observe system and test backend write"""
        if self.dry_run:
            logger.info("[DRY RUN] Would test backend write operations")
            time.sleep(2)
            return

        logger.info(f"Observing for {self.duration}s...")

        # Try to create a small file (simulates backend write)
        test_file = self.path / "fi_chaos_backend_test.tmp"
        try:
            with open(test_file, "w") as f:
                f.write("test" * 1000)
                f.flush()
            test_file.unlink()
            logger.info("✅ Backend write succeeded (disk not full enough)")
        except OSError as e:
            logger.warning(f"⚠️ Backend write FAILED: {e}")
            self.backend_write_error = True

        time.sleep(self.duration)

    def restore(self) -> None:
        """Remove all chaos-created files"""
        if self.dry_run:
            logger.info("[DRY RUN] Would remove all fi_chaos_*.bin files")
            return

        logger.info(f"Cleaning up {len(self.created_files)} files...")
        for file_path in self.created_files:
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        # Clean up any remaining test files
        for pattern in ["fi_chaos_*.bin", "fi_chaos_*.tmp"]:
            for file_path in self.path.glob(pattern):
                try:
                    file_path.unlink()
                    logger.debug(f"Removed {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

        logger.info("✅ Cleanup complete")

    def validate(self) -> dict[str, Any]:
        """Validate drill execution"""
        if self.dry_run:
            return {"passed": True, "path": str(self.path), "details": "Dry run validation"}

        # Get filesystem stats
        import shutil

        try:
            usage = shutil.disk_usage(self.path)
            fs_pct = (usage.used / usage.total) * 100
        except (OSError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"DISK_USAGE_CHECK_FAILED path={self.path} error={e}")
            fs_pct = 0

        return {
            "passed": self.filled_gb > 0 or self.backend_write_error,
            "path": str(self.path),
            "fill_until_pct": self.fill_until_pct,
            "max_gb": self.max_gb,
            "filled_gb": round(self.filled_gb, 2),
            "files_created": len(self.created_files),
            "fs_pct_after": round(fs_pct, 1),
            "backend_write_error_detected": self.backend_write_error,
            "details": f"Filled {self.filled_gb:.2f}GB, write error: {self.backend_write_error}",
        }


def load_policy() -> dict[str, Any]:
    """Load error budget policy from YAML"""
    policy_path = Path("policies/error_budgets.yml")

    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    with open(policy_path) as f:
        return yaml.safe_load(f)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Chaos Drill Runner")
    parser.add_argument(
        "drill_type",
        choices=["network_partition", "corpus_file_lock", "llm_timeout_storm", "disk_full"],
        help="Type of chaos drill to run",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (no actual chaos injection)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute drill (requires --no-dry-run or explicit --execute)",
    )
    parser.add_argument("--output", type=str, help="Output JSON report file")
    parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt (auto-confirm)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent processes (corpus_file_lock)",
    )
    parser.add_argument(
        "--file", type=str, default="storage/corpus.h5", help="File path for corpus_file_lock drill"
    )
    parser.add_argument("--duration", type=int, default=20, help="Duration in seconds for drill")
    parser.add_argument(
        "--port", type=int, default=7001, help="Port to block for network_partition drill"
    )
    parser.add_argument(
        "--join-grace",
        type=int,
        default=None,
        help="Join timeout in seconds (corpus_file_lock, auto-calculated if not set)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="app-mock",
        choices=["app-mock", "http"],
        help="Mode for llm_timeout_storm (app-mock or http)",
    )
    parser.add_argument(
        "--timeout-ms", type=int, default=1500, help="Timeout in milliseconds (llm_timeout_storm)"
    )
    parser.add_argument(
        "--rps", type=int, default=5, help="Requests per second (llm_timeout_storm http mode)"
    )
    parser.add_argument(
        "--path", type=str, default="/tmp/fi-chaos-disk", help="Path for disk_full drill"
    )
    parser.add_argument(
        "--fill-until-pct", type=int, default=95, help="Fill disk until percentage (disk_full)"
    )
    parser.add_argument("--max-gb", type=float, default=2.0, help="Maximum GB to fill (disk_full)")

    args = parser.parse_args()

    # Load policy
    try:
        policy = load_policy()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Get drill config
    drills = policy.get("chaos_drills", {})
    drill_config = drills.get(args.drill_type)

    if not drill_config:
        logger.error(f"Drill type '{args.drill_type}' not found in policy")
        sys.exit(1)

    # Determine dry run mode
    dry_run = not args.execute if args.execute else True

    if not dry_run:
        logger.warning("🔥 EXECUTING REAL CHAOS DRILL (not dry run)")
        if not args.yes:
            confirm = input("Type 'YES' to confirm: ")
            if confirm != "YES":
                logger.info("Drill cancelled")
                sys.exit(0)
        else:
            logger.info("Auto-confirmed via --yes flag")

    # Create drill instance with type-specific parameters
    if args.drill_type == "corpus_file_lock":
        join_grace_val = getattr(args, "join_grace", None)
        drill = CorpusFileLockDrill(
            drill_config,
            dry_run=dry_run,
            file_path=args.file,
            concurrency=args.concurrency,
            duration=args.duration,
            join_grace=join_grace_val,
        )
    elif args.drill_type == "network_partition":
        drill = NetworkPartitionDrill(
            drill_config, dry_run=dry_run, port=args.port, duration=args.duration
        )
    elif args.drill_type == "llm_timeout_storm":
        drill = LLMTimeoutStormDrill(
            drill_config,
            dry_run=dry_run,
            mode=args.mode,
            duration=args.duration,
            concurrency=args.concurrency,
            timeout_ms=args.timeout_ms,
            rps=args.rps,
        )
    elif args.drill_type == "disk_full":
        drill = DiskFullDrill(
            drill_config,
            dry_run=dry_run,
            path=args.path,
            fill_until_pct=args.fill_until_pct,
            max_gb=args.max_gb,
            duration=args.duration,
        )
    else:
        logger.error(f"Drill type '{args.drill_type}' not implemented yet")
        sys.exit(1)

    # Run drill
    result = drill.run()

    # Print summary
    print("\n" + "=" * 60)
    print(f"Chaos Drill Report: {args.drill_type}")
    print("=" * 60)
    print(f"Status: {result['status']}")

    if "duration_sec" in result:
        print(f"Duration: {result['duration_sec']:.1f}s")

    if "validation" in result:
        validation = result["validation"]
        print(f"Validation: {'✅ PASSED' if validation['passed'] else '❌ FAILED'}")

        if "criteria" in validation:
            print("\nSuccess Criteria:")
            for criterion in validation["criteria"]:
                print(f"  • {criterion}")

    print("=" * 60)

    # Save report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        logger.info(f"Report saved to {output_path}")

    # Exit code
    if result["status"] == "SUCCESS":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
