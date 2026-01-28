"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from backend.api.audit.services.audit_service import AuditService
from backend.container import get_container
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.services.workflow.api.public.services.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from backend.services.workflow.services.triage_service import TriageService
from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_task_repository() -> ITaskRepository:
    """Get task repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ITaskRepository instance
    """
    return get_container().get_task_repository()


def get_triage_service_dep() -> TriageService:
    """Get triage service from container.

    Note: This is a temporary bridge during migration.
    Eventually, TriageService will use constructor injection.

    Returns:
        TriageService instance
    """
    return get_container().get_triage_service()


def get_audit_service_dep() -> AuditService:
    """Get audit service from container.

    Note: This is a temporary bridge during migration.
    Eventually, AuditService will be injected directly.

    Returns:
        AuditService instance
    """
    return get_container().get_audit_service()


def get_workflow_logger() -> ILogger:
    """Get logger for workflow service.

    Returns:
        ILogger instance
    """
    return get_logger("workflow")


def get_workflow_orchestrator(
    task_repo: ITaskRepository | None = None,
    logger: ILogger | None = None,
) -> WorkflowOrchestrator:
    """Get workflow orchestrator with injected dependencies.

    FastAPI provider for WorkflowOrchestrator.

    Args:
        task_repo: Task repository (optional, uses default)
        logger: Logger instance (optional, uses default)

    Returns:
        WorkflowOrchestrator instance
    """
    task_repo = task_repo or get_task_repository()
    logger = logger or get_workflow_logger()

    return WorkflowOrchestrator(
        task_repository=task_repo,
        logger=logger,
    )

