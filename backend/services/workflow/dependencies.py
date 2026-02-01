"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().
Direct service/repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import Annotated
from fastapi import Depends

from backend.repositories.audit_repository import AuditRepository
from backend.api.audit.services.audit_service import AuditService
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.repositories.corpus_repository import CorpusRepository
from backend.api.routers.workflow.public.services.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from backend.services.workflow.services.triage_service import TriageService
from backend.services.workflow.services.intelligent_orchestration_service import (
    IntelligentOrchestrationService,
)
from backend.services.workflow.services.workflow_router import WorkflowRouter
from backend.services.workflow.services.workflow_tracker import WorkflowTracker
from backend.services.workflow.interfaces import (
    IIntelligentOrchestrationService,
    IWorkflowOrchestrator,
    IWorkflowRouter,
    IWorkflowTracker,
)
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger
from backend.config import CORPUS_PATH


class WorkflowConfig(BaseModel):
    """Type-safe workflow configuration with validation.

    Validation Rules:
        - max_retries: Must be between 1 and 10
        - timeout_seconds: Must be > 0
        - triage_data_dir: Must be non-empty string (path validation)
        - enable_monitoring: Boolean flag

    Immutability:
        - frozen=True prevents accidental modification after initialization
    """

    max_retries: int = Field(
        ge=1,
        le=10,
        default=3,
        description="Maximum retries for failed workflow steps",
    )
    timeout_seconds: int = Field(
        gt=0,
        default=300,  # 5 minutes
        description="Workflow step timeout in seconds",
    )
    triage_data_dir: str = Field(
        min_length=1,
        default="./data/triage_buffers",
        description="Directory for triage buffer storage",
    )
    enable_monitoring: bool = Field(
        default=True,
        description="Enable workflow monitoring and metrics",
    )
    enable_audit_trail: bool = Field(
        default=True,
        description="Enable audit trail logging for workflow steps",
    )
    max_concurrent_workflows: int = Field(
        ge=1,
        le=100,
        default=10,
        description="Maximum concurrent workflow executions",
    )

    @field_validator("triage_data_dir")
    @classmethod
    def validate_triage_data_dir(cls, v: str) -> str:
        """Ensure triage_data_dir is a valid path format.

        Args:
            v: triage_data_dir value

        Returns:
            Validated triage_data_dir

        Raises:
            ValueError: If path contains invalid characters
        """
        # Basic path validation (not checking if exists - may be created later)
        if ".." in v or v.startswith("/etc") or v.startswith("/sys"):
            raise ValueError("triage_data_dir contains suspicious path")
        return v

    model_config = ConfigDict(frozen=True)


def get_workflow_config() -> WorkflowConfig:
    """Get workflow configuration from environment variables.

    Environment Variables:
        MAX_RETRIES=3 → Maximum retries for workflow steps
        WORKFLOW_TIMEOUT=300 → Timeout in seconds
        TRIAGE_DATA_DIR=./data/triage_buffers → Triage buffer directory
        ENABLE_MONITORING=true → Enable monitoring
        ENABLE_AUDIT_TRAIL=true → Enable audit trail
        MAX_CONCURRENT_WORKFLOWS=10 → Max concurrent executions

    Returns:
        WorkflowConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid (e.g., max_retries > 10)
    """
    return WorkflowConfig(
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        timeout_seconds=int(os.getenv("WORKFLOW_TIMEOUT", "300")),
        triage_data_dir=os.getenv("TRIAGE_DATA_DIR", "./data/triage_buffers"),
        enable_monitoring=os.getenv("ENABLE_MONITORING", "true").lower() == "true",
        enable_audit_trail=os.getenv("ENABLE_AUDIT_TRAIL", "true").lower() == "true",
        max_concurrent_workflows=int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10")),
    )


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
        TriageService instance with type-safe configuration

    Note:
        No longer uses service locator (get_container).
        Config validated via Pydantic (fail-fast on invalid triage_data_dir).
    """
    config = get_workflow_config()
    data_dir = Path(config.triage_data_dir)
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


def get_corpus_repository() -> ICorpusRepository:
    """Get corpus repository for session data.

    Returns:
        ICorpusRepository instance
    """
    return CorpusRepository(CORPUS_PATH)


def get_workflow_orchestrator() -> IWorkflowOrchestrator:
    """Get workflow orchestrator with injected dependencies.

    FastAPI provider for WorkflowOrchestrator.

    Returns:
        IWorkflowOrchestrator instance with task_repository and logger
    """
    return WorkflowOrchestrator(
        task_repository=get_task_repository(),
        logger=get_workflow_logger(),
    )


def get_workflow_router() -> IWorkflowRouter:
    """Get workflow router with injected dependencies.

    FastAPI provider for WorkflowRouter.

    Returns:
        IWorkflowRouter instance with logger
    """
    return WorkflowRouter(logger=get_workflow_logger())


def get_workflow_tracker() -> IWorkflowTracker:
    """Get workflow tracker with injected dependencies.

    FastAPI provider for WorkflowTracker.

    Returns:
        IWorkflowTracker instance with task_repository and logger
    """
    return WorkflowTracker(
        task_repository=get_task_repository(),
        logger=get_workflow_logger(),
    )


def get_intelligent_orchestration_service(
    orchestrator: Annotated[IWorkflowOrchestrator, Depends(get_workflow_orchestrator)],
    router: Annotated[IWorkflowRouter, Depends(get_workflow_router)],
    tracker: Annotated[IWorkflowTracker, Depends(get_workflow_tracker)],
    task_repository: Annotated[ITaskRepository, Depends(get_task_repository)],
    corpus_repository: Annotated[ICorpusRepository, Depends(get_corpus_repository)],
    logger: Annotated[ILogger, Depends(get_workflow_logger)],
) -> IIntelligentOrchestrationService:
    """Provide IntelligentOrchestrationService instance.

    All dependencies auto-resolved by FastAPI Depends().

    Returns:
        IIntelligentOrchestrationService instance
    """
    return IntelligentOrchestrationService(
        orchestrator=orchestrator,
        router=router,
        tracker=tracker,
        task_repository=task_repository,
        corpus_repository=corpus_repository,
        logger=logger,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TYPE ALIASES (Clean Signatures)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WorkflowOrchestratorDep = Annotated[IWorkflowOrchestrator, Depends(get_workflow_orchestrator)]
WorkflowRouterDep = Annotated[IWorkflowRouter, Depends(get_workflow_router)]
WorkflowTrackerDep = Annotated[IWorkflowTracker, Depends(get_workflow_tracker)]
IntelligentOrchestrationDep = Annotated[
    IIntelligentOrchestrationService,
    Depends(get_intelligent_orchestration_service),
]

