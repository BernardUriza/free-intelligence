"""FastAPI Dependency Injection providers for Workflow service.

Provides dependency injection for routers using FastAPI Depends().
Direct service/repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Updated: 2026-02-01 (Phase 2.3 - Worker dependency factories)
Updated: 2026-02-02 (DI Refactor - Singleton factories with @lru_cache)
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
    from backend.repositories.audit_repository import AuditRepository
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
    from backend.repositories.interfaces.itask_repository import ITaskRepository
    from backend.schemas.llm.interfaces.ipreset_loader import IPresetLoader
    from backend.services.llm.interfaces.illm_model_service import ILLMModelService
    from backend.services.soap.interfaces.idecisional_middleware import IDecisionalMiddleware

import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import Annotated
from fastapi import Depends

from backend.services.audit.services.audit_service import AuditService
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository_singleton,
    get_corpus_repository_singleton,
    get_task_repository_singleton,
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


def get_task_repository() -> "ITaskRepository":
    """Get task repository - singleton instance (Phase 4A + P4-3).

    Returns:
        ITaskRepository singleton (shared across endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    return get_task_repository_singleton()


def get_audit_repository() -> "AuditRepository":
    """Get audit repository - singleton instance (Phase 4A + P4-3).

    Returns:
        AuditRepository singleton (shared across endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    from backend.repositories.audit_repository import AuditRepository

    return get_audit_repository_singleton()


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
def _get_audit_service_singleton() -> AuditService:
    """Internal singleton factory for AuditService."""
    return AuditService(repository=get_audit_repository())


def get_audit_service_dep() -> AuditService:
    """Get audit service singleton (Phase 4A + DI Refactor).

    Returns:
        AuditService singleton instance with injected AuditRepository

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return _get_audit_service_singleton()


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


def get_corpus_repository() -> "ICorpusRepository":
    """Get corpus repository - singleton instance (Phase 4A + P4-3).

    Returns:
        ICorpusRepository singleton (shared across endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    return get_corpus_repository_singleton()


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
# WORKER DEPENDENCY FACTORIES (Phase 2.3 - Service Locator Migration)
# Phase 2.3 Fase 6 FIX: Added @lru_cache for singleton behavior
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@lru_cache(maxsize=1)
def _get_policy_loader_singleton() -> IPolicyLoader:
    """Internal singleton factory for PolicyLoader.

    Uses @lru_cache to ensure only ONE instance is created,
    matching the thread-safe singleton behavior of the deprecated
    get_policy_loader() service locator.

    Returns:
        IPolicyLoader singleton instance with policy loaded
    """
    from backend.policy.policy_loader import PolicyLoader

    loader = PolicyLoader()
    loader.load()
    return loader


def get_policy_loader_dep() -> IPolicyLoader:
    """Get policy loader singleton for workers and endpoints.

    Returns:
        IPolicyLoader singleton (same instance for all calls)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
        Single instance created on first call, reused thereafter.

    Note:
        Replaces deprecated get_policy_loader() service locator.
        Workers and endpoints receive this as a dependency.
    """
    return _get_policy_loader_singleton()


@lru_cache(maxsize=1)
def _get_preset_loader_singleton() -> IPresetLoader:
    """Internal singleton factory for PresetLoader."""
    from backend.schemas.llm.preset_loader import PresetLoader

    return PresetLoader()


def get_preset_loader_dep() -> IPresetLoader:
    """Get preset loader singleton for workers.

    Returns:
        IPresetLoader singleton (same instance for all calls)

    Note:
        Replaces deprecated get_preset_loader() service locator.
        Workers receive this as a constructor parameter.
    """
    return _get_preset_loader_singleton()


@lru_cache(maxsize=1)
def _get_decisional_middleware_singleton() -> IDecisionalMiddleware:
    """Internal singleton factory for DecisionalMiddleware."""
    from backend.services.soap.services.decisional_middleware import DecisionalMiddleware

    return DecisionalMiddleware(preset_loader=get_preset_loader_dep())


def get_decisional_middleware_dep() -> IDecisionalMiddleware:
    """Get decisional middleware singleton for SOAP worker.

    Returns:
        IDecisionalMiddleware singleton with preset_loader injected

    Note:
        Replaces deprecated get_decisional_middleware() service locator.
        Handles intelligent SOAP generation orchestration.
    """
    return _get_decisional_middleware_singleton()


@lru_cache(maxsize=1)
def _get_cache_singleton() -> "ICache":
    """Internal singleton factory for LLMCache with default TTL."""
    from backend.infrastructure.cache.cache import LLMCache

    return LLMCache(default_ttl=3600)


def get_cache_dep(ttl: int = 3600) -> "ICache":  # noqa: ARG001
    """Get LLM cache singleton for services.

    Phase 2.3 Mercurio: Cache consolidation.

    Args:
        ttl: DEPRECATED - Ignored. Kept for backward compatibility.
             Singleton uses fixed TTL of 3600s (1 hour).

    Returns:
        ICache singleton instance (LLMCache)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Note:
        Replaces deprecated get_cache() service locator.
        In-memory cache with TTL and Prometheus export.
    """
    _ = ttl  # Ignored - singleton uses fixed TTL
    return _get_cache_singleton()


@lru_cache(maxsize=1)
def _get_llm_model_service_singleton() -> "ILLMModelService":
    """Internal singleton factory for LLMModelService."""
    from backend.services.llm.services.llm_model_service import LLMModelService

    return LLMModelService()


def get_llm_model_service_dep() -> "ILLMModelService":
    """Get LLM model service singleton for model catalog management.

    Phase 2.3 Tierra: Replaces deprecated llm_model_service singleton.

    Returns:
        ILLMModelService singleton instance

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Note:
        The LLMModelService uses internal singleton pattern (__new__),
        but this factory provides the DI-compliant entry point.
    """
    return _get_llm_model_service_singleton()


@lru_cache(maxsize=1)
def _get_catalog_service_singleton() -> "ICatalogService":
    """Internal singleton factory for CatalogService."""
    from backend.domain.prescription.repositories import InMemoryCatalogRepository
    from backend.domain.prescription.services.catalog_service import CatalogService

    repository = InMemoryCatalogRepository()
    return CatalogService(repository=repository)


def get_catalog_service_dep() -> "ICatalogService":
    """Get medication catalog service singleton - SOLID DI factory.

    Phase 2.3 Marte: Replaces deprecated catalog_service singleton.

    Returns:
        ICatalogService singleton instance with InMemoryCatalogRepository

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Note:
        Uses Repository pattern for data access (DIP).
        The CatalogService uses internal singleton pattern (__new__).
    """
    return _get_catalog_service_singleton()


@lru_cache(maxsize=1)
def _get_catalog_repository_singleton() -> "ICatalogRepository":
    """Internal singleton factory for InMemoryCatalogRepository."""
    from backend.domain.prescription.repositories import InMemoryCatalogRepository

    return InMemoryCatalogRepository()


def get_catalog_repository_dep() -> "ICatalogRepository":
    """Get medication catalog repository singleton - SOLID DI factory.

    Phase 2.3 Marte: Provides raw data access for advanced use cases.

    Returns:
        ICatalogRepository singleton instance (InMemoryCatalogRepository)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_catalog_repository_singleton()


@lru_cache(maxsize=1)
def _get_keyvault_secrets_manager_singleton() -> "ISecretsManager":
    """Internal singleton factory for Azure KeyVault SecretsManager."""
    from backend.config.secrets import AzureKeyVaultSecretsManager

    return AzureKeyVaultSecretsManager()


@lru_cache(maxsize=1)
def _get_env_secrets_manager_singleton() -> "ISecretsManager":
    """Internal singleton factory for Env-only SecretsManager."""
    from backend.config.secrets import EnvSecretsManager

    return EnvSecretsManager()


def get_secrets_manager_dep(use_keyvault: bool = True) -> "ISecretsManager":
    """Get secrets manager singleton for services - DI factory.

    Phase 2.3 Jupiter: Centralized secrets management.

    Args:
        use_keyvault: If True, use Azure KeyVault with env fallback.
                     If False, use environment variables only.

    Returns:
        ISecretsManager singleton instance

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
        Two separate singletons for keyvault and env-only modes.

    Note:
        Replaces deprecated get_secret() module-level function.
        Services receive this as a constructor parameter.
    """
    if use_keyvault:
        return _get_keyvault_secrets_manager_singleton()
    return _get_env_secrets_manager_singleton()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GATEKEEPER FACTORY (Phase 2.3 Fase 6)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@lru_cache(maxsize=1)
def _get_gatekeeper_singleton():
    """Internal singleton factory for Gatekeeper."""
    from backend.infrastructure.auth.services.gatekeeper import Gatekeeper

    return Gatekeeper(policy_loader=get_policy_loader_dep())


def get_gatekeeper_dep():
    """Get Gatekeeper singleton with injected dependencies.

    Phase 2.3 Fase 6: Replaces Gatekeeper() with no-args constructor.

    Returns:
        Gatekeeper singleton instance with policy_loader injected

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_gatekeeper_singleton()


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

