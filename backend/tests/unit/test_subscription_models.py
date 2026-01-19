"""
Unit tests for subscription_models module.
Tests SubscriptionPlan model methods.

Coverage targets: backend/models/subscription_models.py
"""

from __future__ import annotations

import pytest
from backend.models.subscription_models import SubscriptionPlan, generate_uuid


class TestGenerateUuid:
    """Tests for generate_uuid function."""

    def test_generates_string(self):
        """Should generate a string."""
        result = generate_uuid()
        assert isinstance(result, str)

    def test_generates_valid_uuid_format(self):
        """Should generate valid UUID format."""
        result = generate_uuid()
        parts = result.split("-")
        assert len(parts) == 5

    def test_generates_unique_values(self):
        """Should generate unique values."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2


class TestSubscriptionPlan:
    """Tests for SubscriptionPlan model."""

    def test_subscription_plan_repr_with_limit(self):
        """Should show max_doctors in repr."""
        plan = SubscriptionPlan()
        plan.name = "pro"
        plan.max_doctors = 10
        
        repr_str = repr(plan)
        
        assert "SubscriptionPlan" in repr_str
        assert "pro" in repr_str
        assert "10" in repr_str

    def test_subscription_plan_repr_unlimited(self):
        """Should show infinity symbol when unlimited."""
        plan = SubscriptionPlan()
        plan.name = "enterprise"
        plan.max_doctors = None
        
        repr_str = repr(plan)
        
        assert "∞" in repr_str

    def test_is_unlimited_when_none(self):
        """Should return True when max_doctors is None."""
        plan = SubscriptionPlan()
        plan.max_doctors = None
        
        assert plan.is_unlimited is True

    def test_is_unlimited_when_limited(self):
        """Should return False when max_doctors has value."""
        plan = SubscriptionPlan()
        plan.max_doctors = 5
        
        assert plan.is_unlimited is False

    def test_is_unlimited_when_zero(self):
        """Should return False when max_doctors is 0."""
        plan = SubscriptionPlan()
        plan.max_doctors = 0
        
        assert plan.is_unlimited is False
