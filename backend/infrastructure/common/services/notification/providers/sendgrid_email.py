"""SendGrid email notification provider.

Email notifications via SendGrid for appointment reminders and check-in codes.

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

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@aurity.io")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "AURITY Clínica")

# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

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
