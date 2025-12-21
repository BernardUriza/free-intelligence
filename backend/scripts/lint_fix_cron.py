#!/usr/bin/env python3.14
"""Continuous lint fix cron job - Runs lint_fix_worker in a loop."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_workers.tasks.lint_fix_worker import lint_fix_worker

logger = get_logger(__name__)


def main():
    """Run continuous lint fixing in batches of 5."""
    logger.info("lint_fix_cron_started")

    batch_size = 5
    sleep_seconds = 60  # Wait 1 minute between batches

    while True:
        try:
            logger.info("starting_lint_fix_batch", batch_size=batch_size)
            result = lint_fix_worker(batch_size)
            data = result

            logger.info(
                "lint_fix_batch_result",
                status=data["status"],
                fixed_count=data["result"]["fixed_count"],
                remaining_errors=data["result"]["remaining_errors"],
                total_errors=data["result"]["total_errors"],
                duration_seconds=data["duration_seconds"]
            )

            if data["result"]["remaining_errors"] == 0:
                logger.info("all_lint_errors_fixed", total_fixed=data["result"]["total_errors"])
                break

            logger.info("waiting_before_next_batch", sleep_seconds=sleep_seconds)
            time.sleep(sleep_seconds)

        except KeyboardInterrupt:
            logger.info("lint_fix_cron_stopped_by_user")
            break
        except Exception as e:
            logger.error("lint_fix_cron_error", error=str(e))
            time.sleep(sleep_seconds)  # Wait before retrying


if __name__ == "__main__":
    main()
