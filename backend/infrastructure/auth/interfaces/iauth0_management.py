"""Interface for Auth0 Management Service - enables dependency injection.

This interface defines the contract for Auth0 user management operations.
Routers depend on this interface for testability and decoupling.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Tabla Periódica K (Potasio)
Created: 2026-02-01
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IAuth0ManagementService(ABC):
    """Abstract interface for Auth0 Management API operations.

    This interface exposes the methods needed by admin routers:
    - list_users, get_user, create_user, update_user, delete_user, block_user
    - get_user_roles, assign_roles, remove_roles
    - list_roles, send_email_verification, link_user_account
    """

    @abstractmethod
    def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search: str | None = None,
        sort: str = "created_at:-1",
    ) -> dict[str, Any]:
        """List users with pagination and search.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page (max 100)
            search: Lucene query string
            sort: Sort field and order

        Returns:
            Dict with 'users', 'total', 'start', 'limit'
        """
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a user by their Auth0 user_id.

        Args:
            user_id: Auth0 user ID (e.g., 'auth0|abc123')

        Returns:
            User data dictionary

        Raises:
            Auth0Error: If user not found or API error
        """
        pass

    @abstractmethod
    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update user attributes in Auth0.

        Args:
            user_id: Auth0 user ID
            updates: Dictionary of fields to update

        Returns:
            Updated user data

        Raises:
            Auth0Error: If update fails
        """
        pass

    @abstractmethod
    def create_user(
        self,
        email: str,
        password: str | None = None,
        name: str | None = None,
        connection: str = "Username-Password-Authentication",
        email_verified: bool = False,
        send_verification_email: bool = True,
    ) -> dict[str, Any]:
        """Create a new user in Auth0.

        Args:
            email: User email
            password: User password (if None, random generated)
            name: User display name
            connection: Auth0 connection name
            email_verified: Pre-verify email
            send_verification_email: Send verification email

        Returns:
            Created user data
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Delete a user from Auth0.

        Args:
            user_id: Auth0 user ID

        Raises:
            Auth0Error: If deletion fails
        """
        pass

    @abstractmethod
    def block_user(self, user_id: str, blocked: bool = True) -> dict[str, Any]:
        """Block or unblock a user.

        Args:
            user_id: Auth0 user ID
            blocked: True to block, False to unblock

        Returns:
            Updated user data
        """
        pass

    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """Get roles assigned to a user.

        Args:
            user_id: Auth0 user ID

        Returns:
            List of role dictionaries
        """
        pass

    @abstractmethod
    def assign_roles(self, user_id: str, role_ids: list[str]) -> None:
        """Assign roles to a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to assign
        """
        pass

    @abstractmethod
    def remove_roles(self, user_id: str, role_ids: list[str]) -> None:
        """Remove roles from a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to remove
        """
        pass

    @abstractmethod
    def list_roles(self) -> list[dict[str, Any]]:
        """List all available roles.

        Returns:
            List of role dictionaries
        """
        pass

    @abstractmethod
    def send_email_verification(self, user_id: str) -> None:
        """Send email verification to user.

        Args:
            user_id: Auth0 user ID
        """
        pass

    @abstractmethod
    def link_user_account(
        self, primary_user_id: str, secondary_user_id: str
    ) -> dict[str, Any]:
        """Link two user accounts.

        Args:
            primary_user_id: Primary user's Auth0 ID
            secondary_user_id: Secondary user's Auth0 ID

        Returns:
            Linked account data
        """
        pass
