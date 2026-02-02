"""Notification Service - Main interface for multi-channel notifications.

Orchestrates SMS and Email notifications via provider implementations.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from notifications.py)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

from datetime import datetime

from backend.infrastructure.common.services.notification.models import (
    NotificationContext,
    NotificationResult,
    NotificationType,
)
from backend.infrastructure.common.services.notification.providers import (
    SendGridEmailProvider,
    TwilioSMSProvider,
)
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Main notification service with multi-channel support.

    Usage:
        service = NotificationService()

        # Send to single channel
        result = await service.send_sms(
            phone="+521234567890",
            notification_type=NotificationType.CHECKIN_CODE,
            context=NotificationContext(
                patient_name="Juan",
                clinic_name="Clínica ABC",
                checkin_code="123456",
            ),
        )

        # Send to all configured channels
        results = await service.send_all(
            phone="+521234567890",
            email="juan@example.com",
            notification_type=NotificationType.APPOINTMENT_REMINDER_24H,
            context=context,
        )
    """

    def __init__(self) -> None:
        self.sms_provider = TwilioSMSProvider()
        self.email_provider = SendGridEmailProvider()

    def get_status(self) -> dict:
        """Get configuration status for all providers."""
        return {
            "sms": {
                "provider": "twilio",
                "configured": self.sms_provider.is_configured(),
            },
            "email": {
                "provider": "sendgrid",
                "configured": self.email_provider.is_configured(),
            },
        }

    async def send_sms(
        self,
        phone: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send SMS notification."""
        return await self.sms_provider.send(phone, notification_type, context)

    async def send_email(
        self,
        email: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send email notification."""
        return await self.email_provider.send(email, notification_type, context)

    async def send_all(
        self,
        notification_type: NotificationType,
        context: NotificationContext,
        phone: str | None = None,
        email: str | None = None,
    ) -> list[NotificationResult]:
        """Send notification to all available channels.

        Args:
            notification_type: Type of notification
            context: Template context data
            phone: Phone number for SMS (optional)
            email: Email address (optional)

        Returns:
            List of results for each channel attempted
        """
        results = []

        if phone and self.sms_provider.is_configured():
            results.append(await self.send_sms(phone, notification_type, context))

        if email and self.email_provider.is_configured():
            results.append(await self.send_email(email, notification_type, context))

        return results


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

# Singleton instance for easy import
notification_service = NotificationService()


# =============================================================================
# REMINDER SCHEDULER (Background task helper)
# =============================================================================


async def schedule_appointment_reminders(
    appointment_id: str,
    scheduled_at: datetime,
    patient_phone: str | None,
    patient_email: str | None,
    context: NotificationContext,
) -> dict:
    """Schedule reminders for an appointment.

    This is a placeholder for actual scheduler integration.
    In production, integrate with:
    - APScheduler for in-process scheduling
    - Celery Beat for distributed scheduling
    - AWS EventBridge for serverless

    Args:
        appointment_id: Unique appointment identifier
        scheduled_at: Appointment datetime
        patient_phone: Patient phone for SMS
        patient_email: Patient email
        context: Notification context

    Returns:
        Dict with scheduled job IDs
    """
    from datetime import timedelta

    reminder_24h = scheduled_at - timedelta(hours=24)
    reminder_1h = scheduled_at - timedelta(hours=1)

    # TODO(human): Implement actual scheduler integration
    # For now, just log what would be scheduled
    logger.info(
        "REMINDERS_SCHEDULED",
        appointment_id=appointment_id,
        reminder_24h=reminder_24h.isoformat(),
        reminder_1h=reminder_1h.isoformat(),
        channels={
            "sms": bool(patient_phone),
            "email": bool(patient_email),
        },
    )

    return {
        "appointment_id": appointment_id,
        "reminders": {
            "24h": reminder_24h.isoformat(),
            "1h": reminder_1h.isoformat(),
        },
        "status": "scheduled",
    }
