"""Lint fix worker - Automated code linting error fixing."""

from __future__ import annotations

import subprocess
import time
from fi_coder.execution.executor import execute_qwen_code
from fi_coder.observability.metrics import MetricsCollector
from fi_common.logging.logger import get_logger
from pathlib import Path
from typing import Any

from backend.workers.tasks.base_worker import WorkerResult, measure_time

logger = get_logger(__name__)


def run_ruff_check(repo_root: Path) -> tuple[int, str]:
    """Run Ruff check and return error count and output."""
    ruff_cmd = ["ruff", "check", "."]  # Check entire repo
    proc = subprocess.run(
        ruff_cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False
    )
    output = proc.stdout + proc.stderr
    # Count backend errors by parsing lines
    lines = output.split('\n')
    backend_errors = [line for line in lines if ':' in line and 'backend/' in line]
    error_count = len(backend_errors)
    return error_count, output


def parse_error_lines(ruff_output: str, max_fixes: int) -> list[dict[str, str]]:
    """Parse ruff output to extract error lines."""
    lines = ruff_output.strip().split('\n')
    error_lines = []
    for line in lines:
        if ':' in line and 'backend/' in line:
            parts = line.split(':', 2)
            if len(parts) >= 3:
                error_lines.append({
                    "file_path": parts[0].strip(),
                    "line_num": parts[1].strip(),
                    "error_desc": parts[2].strip()
                })
    return error_lines[:max_fixes]


def fix_single_error(file_path: str, line_num: str, error_desc: str, repo_root: Path) -> bool:
    """Fix a single linting error using qwen-code."""
    prompt = f"Fix this Ruff linting error in file {file_path} at line {line_num}: {error_desc}\n\nPlease edit the file to fix this specific error."
    result = execute_qwen_code(
        prompt=prompt,
        args="--yolo",  # Allow risky changes
        repo_path=str(repo_root),
        timeout=300,  # 5 minutes per error
    )
    return result["exit_code"] == 0


def lint_fix_batch(batch_size: int = 5) -> dict[str, Any]:
    """Process a batch of linting errors.

    Args:
        batch_size: Number of errors to attempt to fix in this batch.

    Returns:
        Dict with fixed_count, remaining_errors, total_errors, duration_ms
    """
    start_time = time.time()
    repo_root = Path.cwd()  # Use current working directory instead of hardcoded path

    logger.info(
        "lint_fix_batch_started",
        batch_size=batch_size,
        repo_root=str(repo_root)
    )

    metrics = MetricsCollector()
    metrics.record_metric("lint_fix_batch_started", 1.0, tags={"batch_size": str(batch_size)})

    # Run Ruff check
    error_count, ruff_output = run_ruff_check(repo_root)
    metrics.record_metric("lint_errors_found", float(error_count))

    if error_count == 0:
        logger.info("lint_fix_batch_completed", fixed_count=0, remaining_errors=0, total_errors=0)
        return {
            "fixed_count": 0,
            "remaining_errors": 0,
            "total_errors": 0,
            "duration_ms": int((time.time() - start_time) * 1000)
        }

    # Parse errors
    error_lines = parse_error_lines(ruff_output, batch_size)
    logger.info(
        "lint_fix_batch_processing",
        total_errors=error_count,
        processing_errors=len(error_lines)
    )

    fixed_count = 0
    for error in error_lines:
        logger.info(
            "fixing_error",
            file_path=error["file_path"],
            line_num=error["line_num"],
            error_desc=error["error_desc"]
        )
        if fix_single_error(error["file_path"], error["line_num"], error["error_desc"], repo_root):
            fixed_count += 1
            logger.info("error_fixed", file_path=error["file_path"])
        else:
            logger.warning("error_fix_failed", file_path=error["file_path"])

    # Recheck remaining errors
    remaining_count, _ = run_ruff_check(repo_root)
    duration_ms = int((time.time() - start_time) * 1000)

    metrics.record_metric("lint_fix_batch_success", float(fixed_count))
    logger.info(
        "lint_fix_batch_completed",
        fixed_count=fixed_count,
        remaining_errors=remaining_count,
        total_errors=error_count,
        duration_ms=duration_ms
    )

    return {
        "fixed_count": fixed_count,
        "remaining_errors": remaining_count,
        "total_errors": error_count,
        "duration_ms": duration_ms
    }


@measure_time
def lint_fix_worker(batch_size: int = 5) -> WorkerResult:
    """Worker function to process a batch of linting errors.

    Args:
        batch_size: Number of errors to attempt to fix.

    Returns:
        WorkerResult with batch processing results.
    """
    data = lint_fix_batch(batch_size)
    status = "SUCCESS" if data["fixed_count"] > 0 or data["total_errors"] == 0 else "PARTIAL_SUCCESS"
    return WorkerResult(
        status=status,
        result=data
    )