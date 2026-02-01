"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().
Direct service/repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Updated: 2026-02-01 (Phase 2.3 - Worker dependency factories)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.config.interfaces.isecrets_manager import ISecretsManager
    from backend.domain.prescription.interfaces.icatalog_repository import ICatalogRepository
    from backend.domain.prescription.interfaces.icatalog_service import ICatalogService
    from backend.infrastructure.cache.interfaces.icache import ICache
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader
    from backend.schemas.llm.interfaces.ipreset_loader import IPresetLoader
    from backend.services.llm.interfaces.illm_model_service import ILLMModelService
    from backend.services.soap.interfaces.idecisional_middleware import IDecisionalMiddleware

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

    Phase 2.3 migration: Now injects all worker dependencies.

    Returns:
        IWorkflowOrchestrator instance with all dependencies
    """
    return WorkflowOrchestrator(
        task_repository=get_task_repository(),
        workflow_tracker=get_workflow_tracker(),
        policy_loader=get_policy_loader_dep(),
        preset_loader=get_preset_loader_dep(),
        decisional_middleware=get_decisional_middleware_dep(),
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
# WORKER DEPENDENCY FACTORIES (Phase 2.3 - Service Locator Migration)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_policy_loader_dep() -> IPolicyLoader:
    """Get policy loader for workers - direct instantiation.

    Returns:
        IPolicyLoader instance with policy already loaded

    Note:
        Replaces deprecated get_policy_loader() service locator.
        Workers receive this as a constructor parameter.
    """
    from backend.policy.policy_loader import PolicyLoader

    loader = PolicyLoader()
    loader.load()
    return loader


def get_preset_loader_dep() -> IPresetLoader:
    """Get preset loader for workers - direct instantiation.

    Returns:
        IPresetLoader instance

    Note:
        Replaces deprecated get_preset_loader() service locator.
        Workers receive this as a constructor parameter.
    """
    from backend.schemas.llm.preset_loader import PresetLoader

    return PresetLoader()


def get_decisional_middleware_dep() -> IDecisionalMiddleware:
    """Get decisional middleware for SOAP worker - direct instantiation.

    Phase 2.3 Venus: Now injects IPresetLoader dependency.

    Returns:
        IDecisionalMiddleware instance with preset_loader injected

    Note:
        Replaces deprecated get_decisional_middleware() service locator.
        Handles intelligent SOAP generation orchestration.
    """
    from backend.services.soap.services.decisional_middleware import DecisionalMiddleware

    return DecisionalMiddleware(preset_loader=get_preset_loader_dep())


def get_cache_dep(ttl: int = 3600) -> ICache:
    """Get LLM cache for services - direct instantiation.

    Phase 2.3 Mercurio: Cache consolidation.

    Args:
        ttl: Default TTL in seconds (1 hour default)

    Returns:
        ICache instance (LLMCache)

    Note:
        Replaces deprecated get_cache() service locator.
        In-memory cache with TTL and Prometheus export.
    """
    from backend.infrastructure.cache.cache import LLMCache

    return LLMCache(default_ttl=ttl)


def get_llm_model_service_dep() -> ILLMModelService:
    """Get LLM model service for model catalog management.

    Phase 2.3 Tierra: Replaces deprecated llm_model_service singleton.

    Returns:
        ILLMModelService instance

    Note:
        The LLMModelService uses internal singleton pattern (__new__),
        but this factory provides the DI-compliant entry point.
    """
    from backend.services.llm.services.llm_model_service import LLMModelService

    return LLMModelService()


def get_catalog_service_dep() -> ICatalogService:
    """Get medication catalog service - SOLID DI factory.

    Phase 2.3 Marte: Replaces deprecated catalog_service singleton.

    Returns:
        ICatalogService instance with InMemoryCatalogRepository

    Note:
        Uses Repository pattern for data access (DIP).
        The CatalogService uses internal singleton pattern (__new__).
    """
    from backend.domain.prescription.repositories import InMemoryCatalogRepository
    from backend.domain.prescription.services.catalog_service import CatalogService

    repository = InMemoryCatalogRepository()
    return CatalogService(repository=repository)


def get_catalog_repository_dep() -> ICatalogRepository:
    """Get medication catalog repository - SOLID DI factory.

    Phase 2.3 Marte: Provides raw data access for advanced use cases.

    Returns:
        ICatalogRepository instance (InMemoryCatalogRepository)
    """
    from backend.domain.prescription.repositories import InMemoryCatalogRepository

    return InMemoryCatalogRepository()


def get_secrets_manager_dep(use_keyvault: bool = True) -> "ISecretsManager":
    """Get secrets manager for services - DI factory.

    Phase 2.3 Jupiter: Centralized secrets management.

    Args:
        use_keyvault: If True, use Azure KeyVault with env fallback.
                     If False, use environment variables only.

    Returns:
        ISecretsManager instance

    Note:
        Replaces deprecated get_secret() module-level function.
        Services receive this as a constructor parameter.
    """
    from backend.config.secrets import (
        AzureKeyVaultSecretsManager,
        EnvSecretsManager,
    )

    if use_keyvault:
        return AzureKeyVaultSecretsManager()
    return EnvSecretsManager()


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

