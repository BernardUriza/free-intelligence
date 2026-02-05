"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().
Direct service/repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Updated: 2026-02-01 (Phase 2.3 - Worker dependency factories)
Updated: 2026-02-02 (DI Refactor - Singleton factories with @lru_cache)
Updated: 2026-02-02 (DI Refactor - Extracted non-workflow factories to domain modules)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
    from backend.repositories.interfaces.itask_repository import ITaskRepository

import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import Annotated
from fastapi import Depends

from backend.infrastructure.common.repository_singletons import (
    get_corpus_repository,
    get_task_repository,
)
from backend.services.workflow.services.workflow_orchestrator import (
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

# Import domain-specific factories from centralized locations
# Extracted to break circular imports (Phase 2.3 DI Refactor)
from backend.infrastructure.common.policy_provider import get_policy_loader_dep
from backend.schemas.llm.dependencies import get_preset_loader_dep
from backend.services.soap.dependencies import get_decisional_middleware_dep


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


# get_task_repository and get_corpus_repository imported from repository_singletons


@lru_cache(maxsize=1)
def _get_triage_service_singleton() -> TriageService:
    """Internal singleton factory for TriageService.

    Uses @lru_cache to ensure only ONE instance is created.
    Config validated via Pydantic at initialization time.

    Returns:
        TriageService singleton instance
    """
    config = get_workflow_config()
    data_dir = Path(config.triage_data_dir)
    return TriageService(data_dir=data_dir)


def get_triage_service_dep() -> TriageService:
    """Get triage service singleton (Phase 4A + DI Refactor).

    Returns:
        TriageService singleton instance with type-safe configuration

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
        Single instance created on first call, reused thereafter.

    Note:
        No longer uses service locator (get_container).
        Config validated via Pydantic (fail-fast on invalid triage_data_dir).
    """
    return _get_triage_service_singleton()


@lru_cache(maxsize=1)
def _get_workflow_logger_singleton() -> ILogger:
    """Internal singleton factory for workflow logger."""
    return get_logger("workflow")


def get_workflow_logger() -> ILogger:
    """Get logger singleton for workflow service.

    Returns:
        ILogger singleton instance

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_workflow_logger_singleton()


# get_corpus_repository imported from repository_singletons


@lru_cache(maxsize=1)
def _get_workflow_orchestrator_singleton() -> IWorkflowOrchestrator:
    """Internal singleton factory for WorkflowOrchestrator."""
    return WorkflowOrchestrator(
        task_repository=get_task_repository(),
        workflow_tracker=get_workflow_tracker(),
        policy_loader=get_policy_loader_dep(),
        preset_loader=get_preset_loader_dep(),
        decisional_middleware=get_decisional_middleware_dep(),
        logger=get_workflow_logger(),
    )


def get_workflow_orchestrator() -> IWorkflowOrchestrator:
    """Get workflow orchestrator singleton with injected dependencies.

    FastAPI provider for WorkflowOrchestrator.

    Phase 2.3 migration: Now injects all worker dependencies.

    Returns:
        IWorkflowOrchestrator singleton instance with all dependencies

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_workflow_orchestrator_singleton()


@lru_cache(maxsize=1)
def _get_workflow_router_singleton() -> IWorkflowRouter:
    """Internal singleton factory for WorkflowRouter."""
    return WorkflowRouter(logger=get_workflow_logger())


def get_workflow_router() -> IWorkflowRouter:
    """Get workflow router singleton with injected dependencies.

    FastAPI provider for WorkflowRouter.

    Returns:
        IWorkflowRouter singleton instance with logger

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_workflow_router_singleton()


@lru_cache(maxsize=1)
def _get_workflow_tracker_singleton() -> IWorkflowTracker:
    """Internal singleton factory for WorkflowTracker."""
    return WorkflowTracker(
        task_repository=get_task_repository(),
        logger=get_workflow_logger(),
    )


def get_workflow_tracker() -> IWorkflowTracker:
    """Get workflow tracker singleton with injected dependencies.

    FastAPI provider for WorkflowTracker.

    Returns:
        IWorkflowTracker singleton instance with task_repository and logger

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_workflow_tracker_singleton()


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

