"""Notification data models and types.

Enums and dataclasses for notification service.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from notifications.py)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
