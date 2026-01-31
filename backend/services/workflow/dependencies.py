"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().
Direct service/repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from pathlib import Path

from backend.repositories.audit_repository import AuditRepository
from backend.api.audit.services.audit_service import AuditService
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.services.workflow.api.public.services.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from backend.services.workflow.services.triage_service import TriageService
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger
from backend.config import CORPUS_PATH



def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
    """
    return HDF5TaskRepository(CORPUS_PATH)


def get_audit_repository() -> AuditRepository:
    """Get audit repository - direct instantiation (Phase 4A).

    Returns:
        AuditRepository instance

    Note:
        Created as a dependency for AuditService.
        Uses same corpus.h5 path for consistency.
    """
    return AuditRepository(CORPUS_PATH)


def get_triage_service_dep() -> TriageService:
    """Get triage service - direct instantiation (Phase 4A).

    Returns:
        TriageService instance with explicit configuration from environment

    Note:
        No longer uses service locator (get_container).
        Explicit data_dir from TRIAGE_DATA_DIR env var (fallback: ./data/triage_buffers).
    """
    from pathlib import Path
    import os

    data_dir = Path(os.getenv("TRIAGE_DATA_DIR", "./data/triage_buffers"))
    return TriageService(data_dir=data_dir)


def get_audit_service_dep() -> AuditService:
    """Get audit service - direct instantiation (Phase 4A).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())


def get_workflow_logger() -> ILogger:
    """Get logger for workflow service.

    Returns:
        ILogger instance
    """
    return get_logger("workflow")


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get workflow orchestrator with injected dependencies.

    FastAPI provider for WorkflowOrchestrator.

    Returns:
        WorkflowOrchestrator instance with task_repository and logger
    """
    return WorkflowOrchestrator(
        task_repository=get_task_repository(),
        logger=get_workflow_logger(),
    )

