"""
Auth0 Management API Service

Integrates with Auth0 Management API for user administration.
Requires Machine-to-Machine (M2M) application with proper scopes.

Setup Instructions:
1. Create M2M Application in Auth0 Dashboard:
   - Applications → Create Application → Machine to Machine
   - Name: "AURITY Management API"
   - Authorize for "Auth0 Management API"

2. Grant Required Scopes:
   - read:users, create:users, update:users, delete:users
   - read:roles, create:roles, update:roles, delete:roles
   - read:role_members, create:role_members, delete:role_members

3. Configure Environment Variables:
   AUTH0_MANAGEMENT_CLIENT_ID=your_m2m_client_id
   AUTH0_MANAGEMENT_CLIENT_SECRET=your_m2m_client_secret
   AUTH0_DOMAIN=your_tenant.auth0.com

Author: Bernard Uriza
Created: 2025-11-20
"""

import os
import time
from typing import Any, Optional
from datetime import datetime, timedelta
import structlog
from auth0.management import Auth0
from auth0.authentication import GetToken

logger = structlog.get_logger(__name__)


class Auth0ManagementService:
    """
    Service for Auth0 Management API operations.

    Handles user CRUD, role assignment, and invitations.
    Implements token caching to avoid rate limits.
    """

    def __init__(self):
        """Initialize Auth0 Management API client with token caching."""
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.client_id = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
        self.client_secret = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")

        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError(
                "Missing Auth0 Management API credentials. "
                "Set AUTH0_DOMAIN, AUTH0_MANAGEMENT_CLIENT_ID, and AUTH0_MANAGEMENT_CLIENT_SECRET"
            )

        # Token cache
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._mgmt_client: Optional[Auth0] = None

        logger.info(
            "AUTH0_MANAGEMENT_INITIALIZED",
            domain=self.domain,
            client_id=self.client_id[:8] + "...",
        )

    def _get_token(self) -> str:
        """
        Get Management API access token with caching.

        Tokens are cached and refreshed only when expired (1 hour TTL).

        Returns:
            str: Valid access token
        """
        # Return cached token if still valid
        if self._token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                logger.debug("USING_CACHED_TOKEN")
                return self._token

        # Request new token
        logger.info("REQUESTING_NEW_MANAGEMENT_TOKEN")

        get_token = GetToken(self.domain, self.client_id, client_secret=self.client_secret)
        token_response = get_token.client_credentials(f"https://{self.domain}/api/v2/")

        self._token = token_response["access_token"]
        # Auth0 tokens typically expire in 1 hour, cache for 55 min to be safe
        self._token_expires_at = datetime.now() + timedelta(minutes=55)

        logger.info("NEW_TOKEN_ACQUIRED", expires_in_minutes=55)
        return self._token

    def _get_client(self) -> Auth0:
        """
        Get Auth0 Management API client with fresh token.

        Returns:
            Auth0: Configured management client
        """
        token = self._get_token()
        return Auth0(self.domain, token)

    # ========================================================================
    # USER OPERATIONS
    # ========================================================================

    def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search: Optional[str] = None,
        sort: str = "created_at:-1"
    ) -> dict[str, Any]:
        """
        List users with pagination and search.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page (max 100)
            search: Lucene query (e.g., "email:*@example.com")
            sort: Sort field and order (e.g., "created_at:-1")

        Returns:
            dict with 'users', 'total', 'start', 'limit'
        """
        try:
            client = self._get_client()

            # Build query parameters
            params: dict[str, Any] = {
                "page": page,
                "per_page": min(per_page, 100),
                "sort": sort,
                "include_totals": True,
            }

            if search:
                params["q"] = search
                params["search_engine"] = "v3"

            response = client.users.list(**params)

            logger.info(
                "USERS_LISTED",
                total=response.get("total", 0),
                page=page,
                returned=len(response.get("users", [])),
            )

            return response

        except Exception as e:
            logger.error("FAILED_TO_LIST_USERS", error=str(e))
            raise

    def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get user by ID.

        Args:
            user_id: Auth0 user ID (e.g., "auth0|...")

        Returns:
            dict: User data
        """
        try:
            client = self._get_client()
            user = client.users.get(user_id)

            logger.info("USER_RETRIEVED", user_id=user_id, email=user.get("email"))
            return user

        except Exception as e:
            logger.error("FAILED_TO_GET_USER", user_id=user_id, error=str(e))
            raise

    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        name: Optional[str] = None,
        connection: str = "Username-Password-Authentication",
        email_verified: bool = False,
        send_verification_email: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new user.

        Args:
            email: User email
            password: User password (if None, random generated)
            name: User display name
            connection: Auth0 connection (database)
            email_verified: Pre-verify email
            send_verification_email: Send verification email

        Returns:
            dict: Created user data
        """
        try:
            client = self._get_client()

            # Generate secure random password if not provided
            if not password:
                import secrets
                password = secrets.token_urlsafe(32)

            user_data = {
                "email": email,
                "password": password,
                "connection": connection,
                "email_verified": email_verified,
                "verify_email": send_verification_email,
            }

            if name:
                user_data["name"] = name

            user = client.users.create(user_data)

            logger.info(
                "USER_CREATED",
                user_id=user["user_id"],
                email=email,
                email_verified=email_verified,
            )

            return user

        except Exception as e:
            logger.error("FAILED_TO_CREATE_USER", email=email, error=str(e))
            raise

    def update_user(
        self,
        user_id: str,
        updates: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update user attributes.

        Args:
            user_id: Auth0 user ID
            updates: Dict of fields to update (email, name, etc.)

        Returns:
            dict: Updated user data
        """
        try:
            client = self._get_client()
            user = client.users.update(user_id, updates)

            logger.info(
                "USER_UPDATED",
                user_id=user_id,
                fields_updated=list(updates.keys()),
            )

            return user

        except Exception as e:
            logger.error("FAILED_TO_UPDATE_USER", user_id=user_id, error=str(e))
            raise

    def delete_user(self, user_id: str) -> None:
        """
        Delete user permanently.

        Args:
            user_id: Auth0 user ID
        """
        try:
            client = self._get_client()
            client.users.delete(user_id)

            logger.warning("USER_DELETED", user_id=user_id)

        except Exception as e:
            logger.error("FAILED_TO_DELETE_USER", user_id=user_id, error=str(e))
            raise

    def block_user(self, user_id: str, blocked: bool = True) -> dict[str, Any]:
        """
        Block or unblock a user.

        Args:
            user_id: Auth0 user ID
            blocked: True to block, False to unblock

        Returns:
            dict: Updated user data
        """
        try:
            client = self._get_client()
            user = client.users.update(user_id, {"blocked": blocked})

            logger.warning(
                "USER_BLOCKED_STATUS_CHANGED",
                user_id=user_id,
                blocked=blocked,
            )

            return user

        except Exception as e:
            logger.error("FAILED_TO_BLOCK_USER", user_id=user_id, error=str(e))
            raise

    # ========================================================================
    # ROLE OPERATIONS
    # ========================================================================

    def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get roles assigned to user.

        Args:
            user_id: Auth0 user ID

        Returns:
            list: List of role dicts
        """
        try:
            client = self._get_client()
            roles = client.users.list_roles(user_id)

            logger.info(
                "USER_ROLES_RETRIEVED",
                user_id=user_id,
                roles=[r.get("name") for r in roles.get("roles", [])],
            )

            return roles.get("roles", [])

        except Exception as e:
            logger.error("FAILED_TO_GET_USER_ROLES", user_id=user_id, error=str(e))
            raise

    def assign_roles(self, user_id: str, role_ids: list[str]) -> None:
        """
        Assign roles to user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to assign
        """
        try:
            client = self._get_client()
            client.users.add_roles(user_id, {"roles": role_ids})

            logger.info(
                "ROLES_ASSIGNED",
                user_id=user_id,
                role_count=len(role_ids),
            )

        except Exception as e:
            logger.error("FAILED_TO_ASSIGN_ROLES", user_id=user_id, error=str(e))
            raise

    def remove_roles(self, user_id: str, role_ids: list[str]) -> None:
        """
        Remove roles from user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to remove
        """
        try:
            client = self._get_client()
            client.users.remove_roles(user_id, {"roles": role_ids})

            logger.info(
                "ROLES_REMOVED",
                user_id=user_id,
                role_count=len(role_ids),
            )

        except Exception as e:
            logger.error("FAILED_TO_REMOVE_ROLES", user_id=user_id, error=str(e))
            raise

    def list_roles(self) -> list[dict[str, Any]]:
        """
        List all available roles.

        Returns:
            list: List of role dicts
        """
        try:
            client = self._get_client()
            response = client.roles.list()

            logger.info("ROLES_LISTED", count=len(response.get("roles", [])))
            return response.get("roles", [])

        except Exception as e:
            logger.error("FAILED_TO_LIST_ROLES", error=str(e))
            raise

    # ========================================================================
    # INVITATION OPERATIONS
    # ========================================================================

    def send_email_verification(self, user_id: str) -> None:
        """
        Send email verification to user.

        Args:
            user_id: Auth0 user ID
        """
        try:
            client = self._get_client()
            client.jobs.send_verification_email({"user_id": user_id})

            logger.info("VERIFICATION_EMAIL_SENT", user_id=user_id)

        except Exception as e:
            logger.error("FAILED_TO_SEND_VERIFICATION", user_id=user_id, error=str(e))
            raise


# Singleton instance
_auth0_service: Optional[Auth0ManagementService] = None


def get_auth0_service() -> Auth0ManagementService:
    """Get singleton Auth0 Management Service instance."""
    global _auth0_service
    if _auth0_service is None:
        _auth0_service = Auth0ManagementService()
    return _auth0_service
