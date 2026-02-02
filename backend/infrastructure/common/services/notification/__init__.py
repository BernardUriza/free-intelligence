"""Notification Service for FI Receptionist.

Public API for multi-channel notifications (SMS via Twilio, Email via SendGrid).

**Main Entry Point:**
    NotificationService - Main interface with multi-channel support
    notification_service - Singleton instance for easy import

**Data Models:**
    NotificationChannel - Available channels (SMS, EMAIL)
    NotificationType - Notification types (reminders, check-in codes, etc.)
    NotificationResult - Result of notification attempt
    NotificationContext - Template context data

**Providers:**
    TwilioSMSProvider - SMS notifications via Twilio
    SendGridEmailProvider - Email notifications via SendGrid
    NotificationProvider - Abstract base class for providers

**Usage:**
    from backend.infrastructure.common.services.notification import notification_service

    result = await notification_service.send_sms(
        phone="+521234567890",
        notification_type=NotificationType.CHECKIN_CODE,
        context=NotificationContext(
            patient_name="Juan",
            clinic_name="Clínica ABC",
            checkin_code="123456",
        ),
    )

**HIPAA Compliance:**
    - Messages contain ONLY: appointment time, date, location, check-in code
    - NO medical details, diagnoses, provider names, or treatment info
    - Patient consent for SMS/email must be recorded in patient.notification_preferences

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Module refactoring)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

# Public API - Main service
from backend.infrastructure.common.services.notification.service import (
    NotificationService,
    notification_service,
    schedule_appointment_reminders,
)

# Public API - Data models
from backend.infrastructure.common.services.notification.models import (
    NotificationChannel,
    NotificationContext,
    NotificationResult,
    NotificationType,
)

# Public API - Providers (for advanced usage)
from backend.infrastructure.common.services.notification.providers import (
    NotificationProvider,
    SendGridEmailProvider,
    TwilioSMSProvider,
)

__all__ = [
    # Main service
    "NotificationService",
    "notification_service",
    "schedule_appointment_reminders",
    # Data models
    "NotificationChannel",
    "NotificationType",
    "NotificationResult",
    "NotificationContext",
    # Providers (for advanced usage)
    "NotificationProvider",
    "TwilioSMSProvider",
    "SendGridEmailProvider",
]

__version__ = "2.0.0"
