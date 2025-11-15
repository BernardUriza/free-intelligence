"""Task Validation & Startup Diagnostics for Celery Worker.

DEPRECATED: Celery removed as of 2025-11-15.
This file is kept for historical reference only.

Comprehensive validation that ensures all registered tasks exist and are callable.
Prevents silent failures from orphaned task definitions.

Features:
- Validates all registered tasks at startup
- Detects import errors and broken references
- Reports detailed diagnostics
- Fails loudly on inconsistencies (not silently!)

Created: 2025-11-15
Updated: 2025-11-15 (Deprecated - Celery removed)
Card: AUR-LOGGING-IMPROVEMENT
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.logger import get_logger

if TYPE_CHECKING:
    from celery import Celery

logger = get_logger(__name__)


class TaskValidationError(Exception):
    """Raised when task validation fails."""

    pass


class CeleryTaskValidator:
    """Validates Celery task registrations and detects issues."""

    def __init__(self, celery_app: Celery):
        """Initialize validator with Celery app instance.

        Args:
            celery_app: The Celery application instance
        """
        self.celery_app = celery_app
        self.errors = []
        self.warnings = []

    def validate_all_tasks(self) -> bool:
        """Validate all registered tasks comprehensively.

        Returns:
            True if validation passed, False if there were errors

        Raises:
            TaskValidationError: If critical issues found
        """
        logger.info(
            "TASK_VALIDATION_STARTED",
            total_tasks=len(self.celery_app.tasks),
        )

        self._validate_task_registry()
        self._validate_task_callability()
        self._validate_task_imports()

        if self.errors:
            self._report_errors()
            raise TaskValidationError(f"Task validation failed with {len(self.errors)} error(s)")

        if self.warnings:
            self._report_warnings()

        logger.info(
            "TASK_VALIDATION_PASSED",
            total_tasks=len(self.celery_app.tasks),
            warnings=len(self.warnings),
        )
        return True

    def _validate_task_registry(self) -> None:
        """Validate task registry consistency."""
        logger.debug("Validating task registry...")

        registered_names = set(self.celery_app.tasks.keys())

        if not registered_names:
            self.errors.append("No tasks registered! Celery app has empty task registry.")
            return

        logger.info(
            "REGISTERED_TASKS",
            count=len(registered_names),
            tasks=sorted(registered_names),
        )

        # Check for suspicious task names (leftover from old code)
        deprecated_patterns = [
            "deepgram_transcribe",  # Old module names
            "whisper_transcribe",  # Deprecated
            "legacy_",  # Legacy prefix
        ]

        for task_name in registered_names:
            for pattern in deprecated_patterns:
                if pattern in task_name.lower():
                    self.warnings.append(
                        f"⚠️  Found potentially deprecated task: '{task_name}' "
                        f"(matches pattern '{pattern}')"
                    )

    def _validate_task_callability(self) -> None:
        """Validate that all tasks are actually callable."""
        logger.debug("Validating task callability...")

        for task_name, task_obj in self.celery_app.tasks.items():
            # Skip built-in Celery tasks
            if task_name.startswith("celery."):
                continue

            try:
                if not callable(task_obj):
                    self.errors.append(
                        f"Task '{task_name}' is not callable. " f"Type: {type(task_obj)}"
                    )
                    continue

                # Check if task has proper structure
                if not hasattr(task_obj, "apply_async"):
                    self.warnings.append(
                        f"Task '{task_name}' missing apply_async method. "
                        f"May not be a proper Celery task."
                    )

                logger.debug(
                    "TASK_VALIDATED",
                    task_name=task_name,
                    task_type=type(task_obj).__name__,
                )

            except Exception as e:
                self.errors.append(f"Error checking task '{task_name}': {e!s}")

    def _validate_task_imports(self) -> None:
        """Validate that task modules can be imported."""
        logger.debug("Validating task imports...")

        # Common task module locations
        task_modules = [
            "backend.workers.transcription_tasks",
            "backend.workers.diarization_tasks",
        ]

        for module_name in task_modules:
            try:
                __import__(module_name)
                logger.debug("MODULE_IMPORT_OK", module=module_name)
            except ImportError as e:
                self.warnings.append(f"⚠️  Could not import task module '{module_name}': {e!s}")
            except Exception as e:
                self.errors.append(f"Error importing module '{module_name}': {e!s}")

    def _report_errors(self) -> None:
        """Report validation errors prominently."""
        logger.error(
            "TASK_VALIDATION_FAILED",
            error_count=len(self.errors),
        )

        logger.error("=" * 70)
        logger.error("❌ CRITICAL TASK VALIDATION ERRORS ❌")
        logger.error("=" * 70)

        for i, error in enumerate(self.errors, 1):
            logger.error(f"{i}. {error}")

        logger.error("=" * 70)
        logger.error(
            "💥 Worker startup BLOCKED due to validation errors! "
            "Fix issues above before retrying."
        )
        logger.error("=" * 70)

    def _report_warnings(self) -> None:
        """Report validation warnings."""
        logger.warning(
            "TASK_VALIDATION_WARNINGS",
            warning_count=len(self.warnings),
        )

        logger.warning("-" * 70)
        logger.warning("⚠️  TASK VALIDATION WARNINGS ⚠️")
        logger.warning("-" * 70)

        for i, warning in enumerate(self.warnings, 1):
            logger.warning(f"{i}. {warning}")

        logger.warning("-" * 70)


def validate_worker_startup(celery_app: Celery) -> bool:
    """Validate worker at startup.

    This is called before worker starts accepting tasks.
    Fails loudly if there are issues.

    Args:
        celery_app: The Celery application instance

    Returns:
        True if validation passed

    Raises:
        TaskValidationError: If validation failed
    """
    validator = CeleryTaskValidator(celery_app)
    return validator.validate_all_tasks()
