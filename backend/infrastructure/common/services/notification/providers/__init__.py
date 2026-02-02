"""Notification provider implementations.

Public API for all notification providers (SMS, Email, etc.)

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from notifications.py)
Card: Infrastructure Modularization - Quick Wins (Janus Moon)
"""

from __future__ import annotations

from backend.infrastructure.common.services.notification.providers.base import NotificationProvider
from backend.infrastructure.common.services.notification.providers.sendgrid_email import SendGridEmailProvider
from backend.infrastructure.common.services.notification.providers.twilio_sms import TwilioSMSProvider

__all__ = [
    # Base class
    "NotificationProvider",
    # Implementations
    "TwilioSMSProvider",
    "SendGridEmailProvider",
]
