"""Base notification provider interface.

Abstract base class for all notification providers.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from notifications.py)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.infrastructure.common.services.notification.models import (
    NotificationContext,
    NotificationResult,
    NotificationType,
)


class NotificationProvider(ABC):
    """Abstract base for notification providers."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send a notification.

        Args:
            recipient: Recipient identifier (phone number or email)
            notification_type: Type of notification to send
            context: Context data for template rendering

        Returns:
            NotificationResult with success status and message_id
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured.

        Returns:
            True if provider has all required configuration
        """
        ...
