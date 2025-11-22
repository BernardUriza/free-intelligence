"""Notifications API Router.

Endpoints for sending and managing patient notifications.

File: backend/api/public/notifications.py
Card: FI-CHECKIN-003
Created: 2025-11-22
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.database import get_db
from backend.logger import get_logger
from backend.services.notifications import (
    NotificationContext,
    NotificationService,
    NotificationType,
    notification_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# =============================================================================
# SCHEMAS
# =============================================================================


class NotificationStatusResponse(BaseModel):
    """Notification service status."""

    sms: dict
    email: dict


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    notification_type: str = Field(
        ...,
        description="Type: checkin_code, appointment_reminder_24h, appointment_reminder_1h, appointment_confirmation, appointment_cancelled",
    )
    patient_name: str = Field(..., min_length=1, max_length=100)
    clinic_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, pattern=r"^\+?[1-9]\d{9,14}$")
    email: EmailStr | None = None
    doctor_name: str | None = None
    appointment_date: str | None = None
    appointment_time: str | None = None
    checkin_code: str | None = None


class SendNotificationResponse(BaseModel):
    """Response after sending notification."""

    success: bool
    channels_attempted: int
    channels_succeeded: int
    results: list[dict]


class AppointmentReminderRequest(BaseModel):
    """Request to send appointment reminder."""

    appointment_id: str = Field(..., min_length=1)
    clinic_id: str = Field(..., min_length=1)


class ScheduleRemindersRequest(BaseModel):
    """Request to schedule reminders for an appointment."""

    appointment_id: str
    scheduled_at: datetime
    patient_phone: str | None = None
    patient_email: EmailStr | None = None
    patient_name: str
    clinic_name: str
    checkin_code: str | None = None


class ScheduleRemindersResponse(BaseModel):
    """Response after scheduling reminders."""

    appointment_id: str
    reminders: dict
    status: str


# =============================================================================
# DEPENDENCY
# =============================================================================


def get_notification_service() -> NotificationService:
    """Get notification service instance."""
    return notification_service


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/status", response_model=NotificationStatusResponse)
async def get_notification_status(
    service: Annotated[NotificationService, Depends(get_notification_service)],  # noqa: B008
) -> NotificationStatusResponse:
    """Get notification service configuration status.

    Returns which notification channels are configured and available.
    """
    return NotificationStatusResponse(**service.get_status())


@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],  # noqa: B008
) -> SendNotificationResponse:
    """Send a notification via available channels.

    Sends to all provided channels (phone for SMS, email for Email).
    At least one channel must be provided.
    """
    if not request.phone and not request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of phone or email must be provided",
        )

    # Validate notification type
    try:
        notification_type = NotificationType(request.notification_type)
    except ValueError:
        valid_types = [t.value for t in NotificationType]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification_type. Valid types: {valid_types}",
        ) from None

    # Build context
    context = NotificationContext(
        patient_name=request.patient_name,
        clinic_name=request.clinic_name,
        doctor_name=request.doctor_name,
        appointment_date=request.appointment_date,
        appointment_time=request.appointment_time,
        checkin_code=request.checkin_code,
    )

    # Send to all channels
    results = await service.send_all(
        notification_type=notification_type,
        context=context,
        phone=request.phone,
        email=request.email,
    )

    # Build response
    channels_succeeded = sum(1 for r in results if r.success)

    logger.info(
        "NOTIFICATION_SENT",
        notification_type=notification_type.value,
        channels_attempted=len(results),
        channels_succeeded=channels_succeeded,
    )

    return SendNotificationResponse(
        success=channels_succeeded > 0,
        channels_attempted=len(results),
        channels_succeeded=channels_succeeded,
        results=[
            {
                "channel": r.channel.value,
                "success": r.success,
                "message_id": r.message_id,
                "error": r.error,
            }
            for r in results
        ],
    )


@router.post("/appointment/{appointment_id}/reminder")
async def send_appointment_reminder(
    appointment_id: str,
    reminder_type: str = "24h",
    db=Depends(get_db),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> dict:
    """Send appointment reminder notification.

    Fetches appointment details from database and sends reminder
    via patient's preferred notification channels.

    Args:
        appointment_id: UUID of the appointment
        reminder_type: "24h" or "1h"
    """
    from sqlalchemy import text

    # Fetch appointment with patient and clinic info
    query = text("""
        SELECT
            a.appointment_id,
            a.scheduled_at,
            a.checkin_code,
            c.name as clinic_name,
            p.patient_id,
            p.nombre as patient_nombre,
            p.apellido as patient_apellido,
            p.telefono as patient_phone,
            p.email as patient_email
        FROM appointments a
        JOIN clinics c ON a.clinic_id = c.clinic_id
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.appointment_id = :appointment_id
    """)

    result = db.execute(query, {"appointment_id": appointment_id}).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )

    # Determine notification type
    notification_type = (
        NotificationType.APPOINTMENT_REMINDER_24H
        if reminder_type == "24h"
        else NotificationType.APPOINTMENT_REMINDER_1H
    )

    # Build context
    scheduled_at = result.scheduled_at
    context = NotificationContext(
        patient_name=f"{result.patient_nombre} {result.patient_apellido}",
        clinic_name=result.clinic_name,
        appointment_date=scheduled_at.strftime("%d/%m/%Y"),
        appointment_time=scheduled_at.strftime("%H:%M"),
        checkin_code=result.checkin_code,
    )

    # Send notifications
    results = await service.send_all(
        notification_type=notification_type,
        context=context,
        phone=result.patient_phone,
        email=result.patient_email,
    )

    channels_succeeded = sum(1 for r in results if r.success)

    return {
        "appointment_id": appointment_id,
        "reminder_type": reminder_type,
        "channels_attempted": len(results),
        "channels_succeeded": channels_succeeded,
        "results": [
            {
                "channel": r.channel.value,
                "success": r.success,
                "error": r.error,
            }
            for r in results
        ],
    }


@router.post("/schedule-reminders", response_model=ScheduleRemindersResponse)
async def schedule_reminders(
    request: ScheduleRemindersRequest,
    service: Annotated[NotificationService, Depends(get_notification_service)],  # noqa: B008
) -> ScheduleRemindersResponse:
    """Schedule automatic reminders for an appointment.

    Schedules:
    - 24-hour reminder
    - 1-hour reminder

    Note: This is a placeholder endpoint. In production, integrate with
    a job scheduler (APScheduler, Celery Beat, AWS EventBridge).
    """
    from backend.services.notifications import schedule_appointment_reminders

    context = NotificationContext(
        patient_name=request.patient_name,
        clinic_name=request.clinic_name,
        checkin_code=request.checkin_code,
    )

    result = await schedule_appointment_reminders(
        appointment_id=request.appointment_id,
        scheduled_at=request.scheduled_at,
        patient_phone=request.patient_phone,
        patient_email=request.patient_email,
        context=context,
    )

    return ScheduleRemindersResponse(**result)


@router.post("/test/sms")
async def test_sms(
    phone: str,
    service: Annotated[NotificationService, Depends(get_notification_service)],  # noqa: B008
) -> dict:
    """Test SMS delivery (dev/staging only).

    Sends a test SMS to verify Twilio configuration.
    """
    context = NotificationContext(
        patient_name="Test User",
        clinic_name="AURITY Test",
        checkin_code="000000",
    )

    result = await service.send_sms(
        phone=phone,
        notification_type=NotificationType.CHECKIN_CODE,
        context=context,
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
    }


@router.post("/test/email")
async def test_email(
    email: EmailStr,
    service: Annotated[NotificationService, Depends(get_notification_service)],  # noqa: B008
) -> dict:
    """Test email delivery (dev/staging only).

    Sends a test email to verify SendGrid configuration.
    """
    context = NotificationContext(
        patient_name="Test User",
        clinic_name="AURITY Test",
        checkin_code="000000",
        appointment_date="01/01/2025",
        appointment_time="10:00",
    )

    result = await service.send_email(
        email=email,
        notification_type=NotificationType.APPOINTMENT_CONFIRMATION,
        context=context,
    )

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
    }
