"""
Policy API Endpoints
Card: FI-UI-FEAT-204

Provides read-only access to effective policy configuration from fi.policy.yaml

Updated: 2026-02-01 (Phase 2.3 Urano - DI migration for IPolicyLoader)
"""

from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader

from backend.api.policy.dependencies import get_policy_loader_dep
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException

logger = get_logger(__name__)

router = APIRouter(tags=["policy"])


@router.get("/policy")
async def get_policy(
    policy_loader: Annotated["IPolicyLoader", Depends(get_policy_loader_dep)],
) -> dict[str, Any]:
    """
    Get effective policy configuration from fi.policy.yaml

    Returns policy with metadata for UI display.
    """
    try:
        loader = policy_loader

        if loader.policy is None:
            logger.error("POLICY_NOT_LOADED")
            raise HTTPException(
                status_code=503, detail="Policy not loaded. Please check backend logs."
            )

        # Extract metadata from policy
        metadata = loader.policy.get("metadata", {})

        # Build response with policy and metadata
        response = {
            "policy": loader.policy,
            "metadata": {
                "source": str(loader.policy_path),
                "version": metadata.get("version", "unknown"),
                "timestamp": metadata.get("last_updated", "unknown"),
            },
        }

        logger.info(
            "POLICY_FETCHED",
            version=response["metadata"]["version"],
            source=response["metadata"]["source"],
        )

        return response

    except Exception as e:
        logger.error("POLICY_FETCH_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to load policy: {e!s}") from e
