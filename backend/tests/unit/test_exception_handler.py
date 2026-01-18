"""Tests for Exception Handler utility.

Coverage target: 100% of backend/utils/exception_handler.py
"""

from __future__ import annotations

import pytest
from backend.src.fi_coder.utils.exceptions import FIException
from backend.utils.exception_handler import (
    exception_to_response,
    handle_exception,
)
from fastapi import HTTPException, status


# Create test exception subclasses (prefixed with _ to avoid pytest collection)
class _StorageError(FIException):
    """Test storage error."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message, context, status_code=500)


class _NotFoundError(FIException):
    """Test not found error."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message, context, status_code=404)


class _ValidationError(FIException):
    """Test validation error."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message, context, status_code=400)


class _ForbiddenError(FIException):
    """Test forbidden error."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message, context, status_code=403)


class TestHandleException:
    """Test handle_exception function."""

    def test_handles_fi_exception(self):
        """Test handling FIException returns HTTPException."""
        exc = _StorageError("Storage failed", {"session_id": "123"})

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == 500
        assert result.detail["error"] == "_StorageError"
        assert result.detail["message"] == "Storage failed"
        assert result.detail["context"]["session_id"] == "123"

    def test_handles_fi_exception_404(self):
        """Test handling 404 FIException."""
        exc = _NotFoundError("Session not found", {"session_id": "abc"})

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == 404
        assert "not found" in result.detail["message"].lower()

    def test_handles_fi_exception_400(self):
        """Test handling 400 FIException."""
        exc = _ValidationError("Invalid input")

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == 400

    def test_handles_value_error(self):
        """Test handling ValueError returns 400."""
        exc = ValueError("Invalid value")

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == status.HTTP_400_BAD_REQUEST
        assert result.detail["error"] == "ValidationError"
        assert "Invalid value" in result.detail["message"]

    def test_handles_key_error(self):
        """Test handling KeyError returns 404."""
        exc = KeyError("missing_key")

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == status.HTTP_404_NOT_FOUND
        assert result.detail["error"] == "NotFound"

    def test_handles_permission_error(self):
        """Test handling PermissionError returns 403."""
        exc = PermissionError("Access denied")

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == status.HTTP_403_FORBIDDEN
        assert result.detail["error"] == "PermissionDenied"

    def test_handles_generic_exception(self):
        """Test handling generic Exception returns 500."""
        exc = RuntimeError("Something broke")

        result = handle_exception(exc)

        assert isinstance(result, HTTPException)
        assert result.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert result.detail["error"] == "InternalError"

    def test_uses_default_message(self):
        """Test default_message is used for generic exceptions."""
        exc = RuntimeError("Technical details")

        result = handle_exception(exc, default_message="Something went wrong")

        assert result.detail["message"] == "Something went wrong"

    def test_log_error_false_suppresses_logging(self):
        """Test log_error=False doesn't raise."""
        exc = ValueError("No log please")

        # Should not raise
        result = handle_exception(exc, log_error=False)

        assert isinstance(result, HTTPException)


class TestExceptionToResponse:
    """Test exception_to_response function."""

    def test_converts_fi_exception_to_dict(self):
        """Test FIException is converted to response dict."""
        exc = _StorageError("Storage failed")

        result = exception_to_response(exc)

        assert isinstance(result, dict)
        assert "message" in result or "error" in result

    def test_converts_404_exception(self):
        """Test 404 exception is converted correctly."""
        exc = _NotFoundError("Not found")

        result = exception_to_response(exc)

        assert isinstance(result, dict)

    def test_converts_400_exception(self):
        """Test 400 exception is converted correctly."""
        exc = _ValidationError("Bad request")

        result = exception_to_response(exc)

        assert isinstance(result, dict)

    def test_converts_403_exception(self):
        """Test 403 exception is converted correctly."""
        exc = _ForbiddenError("Forbidden")

        result = exception_to_response(exc)

        assert isinstance(result, dict)

    def test_converts_generic_exception(self):
        """Test generic exception is converted to dict."""
        exc = RuntimeError("Generic error")

        result = exception_to_response(exc)

        assert isinstance(result, dict)

    def test_converts_value_error(self):
        """Test ValueError is converted to dict."""
        exc = ValueError("Invalid input")

        result = exception_to_response(exc)

        assert isinstance(result, dict)

    def test_converts_key_error(self):
        """Test KeyError is converted to dict."""
        exc = KeyError("missing")

        result = exception_to_response(exc)

        assert isinstance(result, dict)


class TestFIExceptionBase:
    """Test FIException base class behavior."""

    def test_fi_exception_str_without_context(self):
        """Test FIException string without context."""
        exc = FIException("Simple message")

        assert str(exc) == "Simple message"

    def test_fi_exception_str_with_context(self):
        """Test FIException string with context."""
        exc = FIException("Message", context={"key": "value"})

        result = str(exc)
        assert "Message" in result
        assert "key=value" in result

    def test_fi_exception_default_status_code(self):
        """Test FIException default status code is 500."""
        exc = FIException("Error")

        assert exc.status_code == 500

    def test_fi_exception_custom_status_code(self):
        """Test FIException accepts custom status code."""
        exc = FIException("Not found", status_code=404)

        assert exc.status_code == 404

    def test_fi_exception_context_defaults_to_empty_dict(self):
        """Test FIException context defaults to empty dict."""
        exc = FIException("Error")

        assert exc.context == {}
