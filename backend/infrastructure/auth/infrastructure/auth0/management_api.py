"""Auth0 Management API client for user metadata updates.

Enables automatic synchronization of clinic assignments to Auth0 app_metadata,
so users can access their assigned clinics immediately in next request.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Multi-Tenancy Phase 2
"""

from __future__ import annotations

import httpx

from backend.infrastructure.auth.infrastructure.auth0 import load_auth0_config
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class Auth0ManagementAPI:
    """Auth0 Management API client for updating user metadata.

    Requires AUTH0_MANAGEMENT_API_TOKEN environment variable with scopes:
    - update:users
    - read:users
    """

    def __init__(self):
        config = load_auth0_config()
        self.domain = config.domain
        self.management_api_token = config.management_api_token  # From env
        self.base_url = f"https://{self.domain}/api/v2"

    async def update_user_app_metadata(
        self,
        user_id: str,
        app_metadata: dict
    ) -> None:
        """
        Update user's app_metadata in Auth0.

        Args:
            user_id: Auth0 user ID (e.g., "auth0|user-id")
            app_metadata: Metadata to merge (e.g., {"clinic_id": "clinic-xyz"})

        Raises:
            Does NOT raise on failure - logs error and fails gracefully.
            Manual Auth0 dashboard update required if this fails.

        Example:
            auth0_api = Auth0ManagementAPI()
            await auth0_api.update_user_app_metadata(
                user_id="auth0|user-123",
                app_metadata={"clinic_id": "clinic-abc"}
            )
        """
        if not self.management_api_token:
            logger.error(
                "AUTH0_METADATA_UPDATE_SKIPPED",
                reason="AUTH0_MANAGEMENT_API_TOKEN not set",
                user_id=user_id,
                app_metadata=app_metadata
            )
            # Don't raise - fail gracefully (manual update required)
            return

        url = f"{self.base_url}/users/{user_id}"
        headers = {"Authorization": f"Bearer {self.management_api_token}"}
        payload = {"app_metadata": app_metadata}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                logger.info(
                    "AUTH0_METADATA_UPDATED",
                    user_id=user_id,
                    app_metadata=app_metadata
                )
        except httpx.HTTPStatusError as e:
            logger.error(
                "AUTH0_METADATA_UPDATE_FAILED",
                user_id=user_id,
                status_code=e.response.status_code,
                response_body=e.response.text,
                error=str(e)
            )
            # Don't raise - fail gracefully (manual update required)
        except Exception as e:
            logger.error(
                "AUTH0_METADATA_UPDATE_ERROR",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Don't raise - fail gracefully


# Singleton instance
_auth0_management_api: Auth0ManagementAPI | None = None


def get_auth0_management_api() -> Auth0ManagementAPI:
    """Get singleton Auth0 Management API client.

    Returns:
        Auth0ManagementAPI: Singleton instance
    """
    global _auth0_management_api
    if _auth0_management_api is None:
        _auth0_management_api = Auth0ManagementAPI()
    return _auth0_management_api


__all__ = ["Auth0ManagementAPI", "get_auth0_management_api"]
