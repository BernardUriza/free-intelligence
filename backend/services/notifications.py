"""Notification Service for FI Receptionist.

Handles SMS (Twilio) and Email (SendGrid) notifications for:
- Appointment reminders (24h, 1h before)
- Check-in code delivery
- Appointment confirmations

File: backend/services/notifications.py
Card: FI-CHECKIN-003
Created: 2025-11-22

HIPAA Compliance Notes:
- Messages contain ONLY: appointment time, date, location, check-in code
- NO medical details, diagnoses, provider names, or treatment info
- Patient consent for SMS/email must be recorded in patient.notification_preferences
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from backend.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# SendGrid
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@aurity.io")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "AURITY Clínica")


# =============================================================================
# TYPES & ENUMS
# =============================================================================


class NotificationChannel(str, Enum):
    """Available notification channels."""

    SMS = "sms"
    EMAIL = "email"


class NotificationType(str, Enum):
    """Types of notifications."""

    APPOINTMENT_REMINDER_24H = "appointment_reminder_24h"
    APPOINTMENT_REMINDER_1H = "appointment_reminder_1h"
    CHECKIN_CODE = "checkin_code"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_CANCELLED = "appointment_cancelled"


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    success: bool
    channel: NotificationChannel
    message_id: str | None = None
    error: str | None = None


@dataclass
class NotificationContext:
    """Context data for notification templates."""

    patient_name: str
    clinic_name: str
    doctor_name: str | None = None
    appointment_date: str | None = None
    appointment_time: str | None = None
    checkin_code: str | None = None
    clinic_phone: str | None = None


# =============================================================================
# TEMPLATES
# =============================================================================

SMS_TEMPLATES: dict[NotificationType, str] = {
    NotificationType.APPOINTMENT_REMINDER_24H: (
        "Hola {patient_name}! Recordatorio: tiene cita mañana {appointment_date} "
        "a las {appointment_time} en {clinic_name}. "
        "Código check-in: {checkin_code}. Responda STOP para cancelar SMS."
    ),
    NotificationType.APPOINTMENT_REMINDER_1H: (
        "{patient_name}: Su cita es en 1 hora ({appointment_time}) en {clinic_name}. "
        "Código check-in: {checkin_code}. Llegue 10 min antes."
    ),
    NotificationType.CHECKIN_CODE: (
        "Su código de check-in para {clinic_name} es: {checkin_code}. "
        "Válido hasta 2 horas después de su cita."
    ),
    NotificationType.APPOINTMENT_CONFIRMATION: (
        "Cita confirmada: {appointment_date} a las {appointment_time} en {clinic_name}. "
        "Código check-in: {checkin_code}."
    ),
    NotificationType.APPOINTMENT_CANCELLED: (
        "Su cita del {appointment_date} en {clinic_name} ha sido cancelada. "
        "Contacte a la clínica para reprogramar."
    ),
}

EMAIL_SUBJECTS: dict[NotificationType, str] = {
    NotificationType.APPOINTMENT_REMINDER_24H: "Recordatorio: Cita mañana en {clinic_name}",
    NotificationType.APPOINTMENT_REMINDER_1H: "Su cita es en 1 hora - {clinic_name}",
    NotificationType.CHECKIN_CODE: "Su código de check-in - {clinic_name}",
    NotificationType.APPOINTMENT_CONFIRMATION: "Cita confirmada - {clinic_name}",
    NotificationType.APPOINTMENT_CANCELLED: "Cita cancelada - {clinic_name}",
}

EMAIL_TEMPLATES: dict[NotificationType, str] = {
    NotificationType.APPOINTMENT_REMINDER_24H: """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #0066cc; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">Recordatorio de Cita</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9;">
        <p>Hola <strong>{patient_name}</strong>,</p>
        <p>Le recordamos que tiene una cita programada:</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Fecha:</strong> {appointment_date}</p>
            <p><strong>Hora:</strong> {appointment_time}</p>
            <p><strong>Clínica:</strong> {clinic_name}</p>
        </div>
        <div style="background: #e8f4ff; padding: 20px; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 10px 0;">Su código de check-in:</p>
            <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 0; color: #0066cc;">
                {checkin_code}
            </p>
            <p style="font-size: 12px; color: #666; margin: 10px 0 0 0;">
                Válido hasta 2 horas después de su cita
            </p>
        </div>
        <p style="margin-top: 20px;">Por favor llegue 10 minutos antes de su cita.</p>
    </div>
    <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
        <p>Este es un mensaje automático de {clinic_name}</p>
    </div>
</body>
</html>
""",
    NotificationType.APPOINTMENT_REMINDER_1H: """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #ff6600; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">¡Su cita es en 1 hora!</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9;">
        <p>Hola <strong>{patient_name}</strong>,</p>
        <p>Su cita está próxima:</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Hora:</strong> {appointment_time}</p>
            <p><strong>Clínica:</strong> {clinic_name}</p>
        </div>
        <div style="background: #fff3e8; padding: 20px; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 10px 0;">Código de check-in:</p>
            <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 0; color: #ff6600;">
                {checkin_code}
            </p>
        </div>
    </div>
</body>
</html>
""",
    NotificationType.CHECKIN_CODE: """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #00cc66; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">Código de Check-in</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9; text-align: center;">
        <p>Hola <strong>{patient_name}</strong>,</p>
        <p>Su código de check-in para {clinic_name}:</p>
        <div style="background: #e8fff0; padding: 30px; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 48px; font-weight: bold; letter-spacing: 12px; margin: 0; color: #00cc66;">
                {checkin_code}
            </p>
        </div>
        <p style="color: #666;">Válido hasta 2 horas después de su cita programada.</p>
    </div>
</body>
</html>
""",
    NotificationType.APPOINTMENT_CONFIRMATION: """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #0066cc; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">Cita Confirmada</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9;">
        <p>Hola <strong>{patient_name}</strong>,</p>
        <p>Su cita ha sido confirmada:</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Fecha:</strong> {appointment_date}</p>
            <p><strong>Hora:</strong> {appointment_time}</p>
            <p><strong>Clínica:</strong> {clinic_name}</p>
        </div>
        <div style="background: #e8f4ff; padding: 20px; border-radius: 8px; text-align: center;">
            <p style="margin: 0 0 10px 0;">Código de check-in:</p>
            <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 0; color: #0066cc;">
                {checkin_code}
            </p>
        </div>
    </div>
</body>
</html>
""",
    NotificationType.APPOINTMENT_CANCELLED: """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #cc0000; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">Cita Cancelada</h1>
    </div>
    <div style="padding: 30px; background: #f9f9f9;">
        <p>Hola <strong>{patient_name}</strong>,</p>
        <p>Su cita del <strong>{appointment_date}</strong> en <strong>{clinic_name}</strong> ha sido cancelada.</p>
        <p>Por favor contacte a la clínica para reprogramar su cita.</p>
    </div>
</body>
</html>
""",
}


# =============================================================================
# ABSTRACT PROVIDER
# =============================================================================


class NotificationProvider(ABC):
    """Abstract base for notification providers."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send a notification."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        ...


# =============================================================================
# TWILIO SMS PROVIDER
# =============================================================================


class TwilioSMSProvider(NotificationProvider):
    """Twilio SMS notification provider."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Lazy-load Twilio client."""
        if self._client is None:
            try:
                from twilio.rest import Client

                self._client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except ImportError:
                logger.warning("TWILIO_NOT_INSTALLED", message="Install twilio package")
                return None
        return self._client

    def is_configured(self) -> bool:
        """Check if Twilio is configured."""
        return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER])

    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send SMS via Twilio."""
        if not self.is_configured():
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SMS,
                error="Twilio not configured",
            )

        client = self._get_client()
        if client is None:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SMS,
                error="Twilio client not available",
            )

        template = SMS_TEMPLATES.get(notification_type)
        if not template:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SMS,
                error=f"No SMS template for {notification_type}",
            )

        # Format message with context
        message_body = template.format(
            patient_name=context.patient_name,
            clinic_name=context.clinic_name,
            doctor_name=context.doctor_name or "",
            appointment_date=context.appointment_date or "",
            appointment_time=context.appointment_time or "",
            checkin_code=context.checkin_code or "",
            clinic_phone=context.clinic_phone or "",
        )

        try:
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=recipient,
            )

            logger.info(
                "SMS_SENT",
                recipient=recipient[-4:],  # Log only last 4 digits for privacy
                notification_type=notification_type.value,
                message_sid=message.sid,
            )

            return NotificationResult(
                success=True,
                channel=NotificationChannel.SMS,
                message_id=message.sid,
            )

        except Exception as e:
            logger.error(
                "SMS_SEND_FAILED",
                recipient=recipient[-4:],
                notification_type=notification_type.value,
                error=str(e),
            )
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SMS,
                error=str(e),
            )


# =============================================================================
# SENDGRID EMAIL PROVIDER
# =============================================================================


class SendGridEmailProvider(NotificationProvider):
    """SendGrid email notification provider."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Lazy-load SendGrid client."""
        if self._client is None:
            try:
                from sendgrid import SendGridAPIClient

                self._client = SendGridAPIClient(SENDGRID_API_KEY)
            except ImportError:
                logger.warning("SENDGRID_NOT_INSTALLED", message="Install sendgrid package")
                return None
        return self._client

    def is_configured(self) -> bool:
        """Check if SendGrid is configured."""
        return bool(SENDGRID_API_KEY)

    async def send(
        self,
        recipient: str,
        notification_type: NotificationType,
        context: NotificationContext,
    ) -> NotificationResult:
        """Send email via SendGrid."""
        if not self.is_configured():
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error="SendGrid not configured",
            )

        client = self._get_client()
        if client is None:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error="SendGrid client not available",
            )

        template = EMAIL_TEMPLATES.get(notification_type)
        subject_template = EMAIL_SUBJECTS.get(notification_type)
        if not template or not subject_template:
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=f"No email template for {notification_type}",
            )

        # Format content with context
        format_args = {
            "patient_name": context.patient_name,
            "clinic_name": context.clinic_name,
            "doctor_name": context.doctor_name or "",
            "appointment_date": context.appointment_date or "",
            "appointment_time": context.appointment_time or "",
            "checkin_code": context.checkin_code or "",
            "clinic_phone": context.clinic_phone or "",
        }
        html_content = template.format(**format_args)
        subject = subject_template.format(**format_args)

        try:
            from sendgrid.helpers.mail import Content, Email, Mail, To

            message = Mail(
                from_email=Email(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
                to_emails=To(recipient),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            response = client.send(message)

            logger.info(
                "EMAIL_SENT",
                recipient=recipient.split("@")[0][:3] + "***",  # Partial email for privacy
                notification_type=notification_type.value,
                status_code=response.status_code,
            )

            return NotificationResult(
                success=response.status_code in (200, 202),
                channel=NotificationChannel.EMAIL,
                message_id=response.headers.get("X-Message-Id"),
            )

        except Exception as e:
            logger.error(
                "EMAIL_SEND_FAILED",
                recipient=recipient.split("@")[0][:3] + "***",
                notification_type=notification_type.value,
                error=str(e),
            )
            return NotificationResult(
                success=False,
                channel=NotificationChannel.EMAIL,
                error=str(e),
            )


# =============================================================================
# NOTIFICATION SERVICE (Main Interface)
# =============================================================================


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
