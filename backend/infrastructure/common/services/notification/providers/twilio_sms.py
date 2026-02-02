"""Twilio SMS notification provider.

SMS notifications via Twilio for appointment reminders and check-in codes.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from notifications.py)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

import os

from backend.infrastructure.common.services.notification.models import (
    NotificationChannel,
    NotificationContext,
    NotificationResult,
    NotificationType,
)
from backend.infrastructure.common.services.notification.providers.base import NotificationProvider
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# =============================================================================
# SMS TEMPLATES
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
