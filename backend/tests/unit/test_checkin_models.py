"""
Unit tests for checkin_models helper functions.
Tests utility functions like UUID generation, code generation, and expiry calculations.

Coverage targets: backend/models/checkin_models.py helper functions
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.models.checkin_models import (
    AppointmentStatus,
    AppointmentType,
    CheckinStep,
    DeviceType,
    PendingActionStatus,
    PendingActionType,
    generate_checkin_code,
    generate_uuid,
    get_checkin_code_expiry,
    get_qr_expiry,
    get_session_expiry,
)


class TestGenerateUuid:
    """Tests for generate_uuid function."""

    def test_generates_valid_uuid_string(self):
        """Should generate valid UUID string."""
        uuid_str = generate_uuid()
        
        assert isinstance(uuid_str, str)
        assert len(uuid_str) == 36  # Standard UUID format

    def test_generates_unique_uuids(self):
        """Should generate unique UUIDs each call."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        uuid3 = generate_uuid()
        
        assert uuid1 != uuid2
        assert uuid2 != uuid3
        assert uuid1 != uuid3

    def test_uuid_format(self):
        """Should match UUID format with hyphens."""
        uuid_str = generate_uuid()
        parts = uuid_str.split("-")
        
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestGenerateCheckinCode:
    """Tests for generate_checkin_code function."""

    def test_generates_6_digit_code(self):
        """Should generate 6-digit code."""
        code = generate_checkin_code()
        
        assert isinstance(code, str)
        assert len(code) == 6

    def test_code_is_numeric(self):
        """Should contain only digits."""
        code = generate_checkin_code()
        
        assert code.isdigit()

    def test_generates_different_codes(self):
        """Should generate different codes (probabilistically)."""
        codes = {generate_checkin_code() for _ in range(100)}
        
        # With 1M possible codes, 100 should be mostly unique
        assert len(codes) >= 90


class TestGetCheckinCodeExpiry:
    """Tests for get_checkin_code_expiry function."""

    def test_returns_end_of_today(self):
        """Should return end of today (23:59:59.999999)."""
        expiry = get_checkin_code_expiry()
        
        assert expiry.hour == 23
        assert expiry.minute == 59
        assert expiry.second == 59
        assert expiry.microsecond == 999999

    def test_returns_datetime_with_utc(self):
        """Should return UTC datetime."""
        expiry = get_checkin_code_expiry()
        
        assert expiry.tzinfo is not None

    def test_expiry_is_future(self):
        """Should be in the future or same second."""
        now = datetime.now(UTC)
        expiry = get_checkin_code_expiry()
        
        assert expiry >= now.replace(hour=0, minute=0, second=0)


class TestGetSessionExpiry:
    """Tests for get_session_expiry function."""

    def test_returns_15_minutes_future(self):
        """Should return time 15 minutes in future."""
        before = datetime.now(UTC)
        expiry = get_session_expiry()
        after = datetime.now(UTC)
        
        expected_min = before + timedelta(minutes=15)
        expected_max = after + timedelta(minutes=15)
        
        assert expected_min <= expiry <= expected_max

    def test_returns_datetime_with_timezone(self):
        """Should return timezone-aware datetime."""
        expiry = get_session_expiry()
        
        assert expiry.tzinfo is not None


class TestGetQrExpiry:
    """Tests for get_qr_expiry function."""

    def test_returns_5_minutes_future(self):
        """Should return time 5 minutes in future."""
        before = datetime.now(UTC)
        expiry = get_qr_expiry()
        after = datetime.now(UTC)
        
        expected_min = before + timedelta(minutes=5)
        expected_max = after + timedelta(minutes=5)
        
        assert expected_min <= expiry <= expected_max

    def test_returns_datetime_with_timezone(self):
        """Should return timezone-aware datetime."""
        expiry = get_qr_expiry()
        
        assert expiry.tzinfo is not None


class TestCheckinStep:
    """Tests for CheckinStep enum."""

    def test_scan_qr_step(self):
        """Should have scan_qr step."""
        assert CheckinStep.SCAN_QR.value == "scan_qr"

    def test_identify_step(self):
        """Should have identify step."""
        assert CheckinStep.IDENTIFY.value == "identify"

    def test_confirm_identity_step(self):
        """Should have confirm_identity step."""
        assert CheckinStep.CONFIRM_IDENTITY.value == "confirm_identity"

    def test_pending_actions_step(self):
        """Should have pending_actions step."""
        assert CheckinStep.PENDING_ACTIONS.value == "pending_actions"

    def test_success_step(self):
        """Should have success step."""
        assert CheckinStep.SUCCESS.value == "success"

    def test_error_step(self):
        """Should have error step."""
        assert CheckinStep.ERROR.value == "error"


class TestDeviceType:
    """Tests for DeviceType enum."""

    def test_mobile_type(self):
        """Should have mobile type."""
        assert DeviceType.MOBILE.value == "mobile"

    def test_kiosk_type(self):
        """Should have kiosk type."""
        assert DeviceType.KIOSK.value == "kiosk"

    def test_tablet_type(self):
        """Should have tablet type."""
        assert DeviceType.TABLET.value == "tablet"

    def test_all_types(self):
        """Should have exactly 3 device types."""
        types = list(DeviceType)
        assert len(types) == 3


class TestAppointmentStatus:
    """Tests for AppointmentStatus enum."""

    def test_scheduled_status(self):
        """Should have scheduled status."""
        assert AppointmentStatus.SCHEDULED.value == "scheduled"

    def test_confirmed_status(self):
        """Should have confirmed status."""
        assert AppointmentStatus.CONFIRMED.value == "confirmed"

    def test_checked_in_status(self):
        """Should have checked_in status."""
        assert AppointmentStatus.CHECKED_IN.value == "checked_in"

    def test_in_progress_status(self):
        """Should have in_progress status."""
        assert AppointmentStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_status(self):
        """Should have completed status."""
        assert AppointmentStatus.COMPLETED.value == "completed"

    def test_cancelled_status(self):
        """Should have cancelled status."""
        assert AppointmentStatus.CANCELLED.value == "cancelled"

    def test_no_show_status(self):
        """Should have no_show status."""
        assert AppointmentStatus.NO_SHOW.value == "no_show"


class TestAppointmentType:
    """Tests for AppointmentType enum."""

    def test_first_visit_type(self):
        """Should have first_visit type."""
        assert AppointmentType.FIRST_VISIT.value == "first_visit"

    def test_follow_up_type(self):
        """Should have follow_up type."""
        assert AppointmentType.FOLLOW_UP.value == "follow_up"

    def test_procedure_type(self):
        """Should have procedure type."""
        assert AppointmentType.PROCEDURE.value == "procedure"

    def test_emergency_type(self):
        """Should have emergency type."""
        assert AppointmentType.EMERGENCY.value == "emergency"

    def test_telemedicine_type(self):
        """Should have telemedicine type."""
        assert AppointmentType.TELEMEDICINE.value == "telemedicine"

    def test_all_appointment_types(self):
        """Should have exactly 5 appointment types."""
        types = list(AppointmentType)
        assert len(types) == 5


class TestPendingActionType:
    """Tests for PendingActionType enum."""

    def test_update_contact(self):
        """Should have update_contact type."""
        assert PendingActionType.UPDATE_CONTACT.value == "update_contact"

    def test_update_insurance(self):
        """Should have update_insurance type."""
        assert PendingActionType.UPDATE_INSURANCE.value == "update_insurance"

    def test_sign_consent(self):
        """Should have sign_consent type."""
        assert PendingActionType.SIGN_CONSENT.value == "sign_consent"

    def test_sign_privacy(self):
        """Should have sign_privacy type."""
        assert PendingActionType.SIGN_PRIVACY.value == "sign_privacy"

    def test_pay_copay(self):
        """Should have pay_copay type."""
        assert PendingActionType.PAY_COPAY.value == "pay_copay"

    def test_pay_balance(self):
        """Should have pay_balance type."""
        assert PendingActionType.PAY_BALANCE.value == "pay_balance"

    def test_upload_labs(self):
        """Should have upload_labs type."""
        assert PendingActionType.UPLOAD_LABS.value == "upload_labs"

    def test_upload_imaging(self):
        """Should have upload_imaging type."""
        assert PendingActionType.UPLOAD_IMAGING.value == "upload_imaging"

    def test_fill_questionnaire(self):
        """Should have fill_questionnaire type."""
        assert PendingActionType.FILL_QUESTIONNAIRE.value == "fill_questionnaire"

    def test_verify_identity(self):
        """Should have verify_identity type."""
        assert PendingActionType.VERIFY_IDENTITY.value == "verify_identity"

    def test_all_action_types(self):
        """Should have exactly 10 action types."""
        types = list(PendingActionType)
        assert len(types) == 10


class TestPendingActionStatus:
    """Tests for PendingActionStatus enum."""

    def test_pending_status(self):
        """Should have pending status."""
        assert PendingActionStatus.PENDING.value == "pending"

    def test_in_progress_status(self):
        """Should have in_progress status."""
        assert PendingActionStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_status(self):
        """Should have completed status."""
        assert PendingActionStatus.COMPLETED.value == "completed"

    def test_skipped_status(self):
        """Should have skipped status."""
        assert PendingActionStatus.SKIPPED.value == "skipped"

    def test_all_statuses(self):
        """Should have exactly 4 statuses."""
        statuses = list(PendingActionStatus)
        assert len(statuses) == 4