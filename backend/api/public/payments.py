"""FI Receptionist Payments API endpoints.

Stripe integration for copay and balance payments during check-in.
Supports payment intent creation, webhook handling, and payment status tracking.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-002
"""

from __future__ import annotations

import os
import stripe
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.logger import get_logger
from backend.models.checkin_models import (
    Appointment,
    PendingAction,
    PendingActionStatus,
    PendingActionType,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])

# =============================================================================
# STRIPE CONFIGURATION
# =============================================================================

# Load Stripe keys from environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =============================================================================
# SCHEMAS
# =============================================================================


class CreatePaymentIntentRequest(BaseModel):
    """Request to create a Stripe payment intent."""

    action_id: str = Field(..., description="Pending action ID for the payment")
    appointment_id: str = Field(..., description="Appointment ID")


class CreatePaymentIntentResponse(BaseModel):
    """Response with Stripe payment intent details."""

    client_secret: str = Field(..., description="Stripe client secret for frontend")
    payment_intent_id: str = Field(..., description="Payment intent ID")
    amount: int = Field(..., description="Amount in cents (MXN)")
    currency: str = Field(default="mxn", description="Currency code")
    publishable_key: str = Field(..., description="Stripe publishable key")


class PaymentStatusResponse(BaseModel):
    """Payment status response."""

    payment_intent_id: str
    status: str
    amount: int
    currency: str
    action_id: str | None = None
    completed_at: str | None = None


class StripeConfigResponse(BaseModel):
    """Stripe configuration for frontend."""

    publishable_key: str
    enabled: bool


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def verify_stripe_configured() -> None:
    """Verify Stripe is properly configured."""
    if not STRIPE_SECRET_KEY:
        logger.error("STRIPE_NOT_CONFIGURED", message="Stripe secret key not set")
        raise HTTPException(
            status_code=503,
            detail="Payment service not configured. Contact support.",
        )


def get_pending_action_for_payment(
    db: Session, action_id: str, appointment_id: str
) -> PendingAction:
    """Get and validate a pending action for payment."""
    action = (
        db.query(PendingAction)
        .filter(
            PendingAction.action_id == action_id,
            PendingAction.appointment_id == appointment_id,
            PendingAction.action_type.in_(
                [PendingActionType.PAY_COPAY, PendingActionType.PAY_BALANCE]
            ),
        )
        .first()
    )

    if not action:
        raise HTTPException(
            status_code=404,
            detail="Payment action not found or not a payment type",
        )

    if action.status == PendingActionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Payment has already been completed",
        )

    if not action.amount or action.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment amount",
        )

    return action


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/config", response_model=StripeConfigResponse)
async def get_stripe_config() -> StripeConfigResponse:
    """
    Get Stripe configuration for frontend.

    Returns publishable key and whether payments are enabled.
    """
    return StripeConfigResponse(
        publishable_key=STRIPE_PUBLISHABLE_KEY or "",
        enabled=bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY),
    )


@router.post("/create-intent", response_model=CreatePaymentIntentResponse)
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    db: Session = Depends(get_db_dependency),  # noqa: B008  # noqa: B008
) -> CreatePaymentIntentResponse:
    """
    Create a Stripe payment intent for a pending payment action.

    This endpoint creates a payment intent that the frontend can use
    to process the payment through Stripe Elements.

    Args:
        request: Payment intent creation request
        db: Database session

    Returns:
        Payment intent details including client secret for frontend
    """
    verify_stripe_configured()

    # Get and validate the pending action
    action = get_pending_action_for_payment(db, request.action_id, request.appointment_id)

    # Get appointment for metadata
    appointment = (
        db.query(Appointment).filter(Appointment.appointment_id == request.appointment_id).first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Convert amount to cents (Stripe uses smallest currency unit)
    amount_cents = int(action.amount * 100)
    currency = (action.currency or "MXN").lower()

    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            metadata={
                "action_id": str(action.action_id),
                "appointment_id": str(appointment.appointment_id),
                "clinic_id": str(appointment.clinic_id),
                "patient_id": str(appointment.patient_id),
                "action_type": action.action_type.value,
            },
            description=f"{action.title} - {action.description or 'Clinic payment'}",
            automatic_payment_methods={"enabled": True},
        )

        # Update action with payment intent ID
        action.payment_intent_id = intent.id
        action.status = PendingActionStatus.IN_PROGRESS
        db.commit()

        logger.info(
            "PAYMENT_INTENT_CREATED",
            payment_intent_id=intent.id,
            action_id=str(action.action_id),
            amount_cents=amount_cents,
            currency=currency,
        )

        return CreatePaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id,
            amount=amount_cents,
            currency=currency,
            publishable_key=STRIPE_PUBLISHABLE_KEY,
        )

    except stripe.error.StripeError as e:
        logger.error(
            "STRIPE_ERROR",
            error=str(e),
            action_id=str(action.action_id),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Payment service error: {e!s}",
        ) from e


@router.get("/status/{payment_intent_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_intent_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> PaymentStatusResponse:
    """
    Get the status of a payment intent.

    Args:
        payment_intent_id: Stripe payment intent ID
        db: Database session

    Returns:
        Current payment status
    """
    verify_stripe_configured()

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # Find associated action
        action = (
            db.query(PendingAction)
            .filter(PendingAction.payment_intent_id == payment_intent_id)
            .first()
        )

        return PaymentStatusResponse(
            payment_intent_id=intent.id,
            status=intent.status,
            amount=intent.amount,
            currency=intent.currency,
            action_id=str(action.action_id) if action else None,
            completed_at=(
                action.completed_at.isoformat() if action and action.completed_at else None
            ),
        )

    except stripe.error.StripeError as e:
        logger.error("STRIPE_RETRIEVE_ERROR", error=str(e))
        raise HTTPException(status_code=404, detail="Payment not found") from e


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db_dependency),  # noqa: B008
):
    """
    Handle Stripe webhook events.

    This endpoint receives events from Stripe when payment status changes.
    It updates the corresponding pending action status.

    Events handled:
    - payment_intent.succeeded: Mark action as completed
    - payment_intent.payment_failed: Mark action as pending (retry)
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET_NOT_CONFIGURED")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    # Get raw body for signature verification
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        logger.error("WEBHOOK_INVALID_PAYLOAD")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("WEBHOOK_INVALID_SIGNATURE")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(
        "STRIPE_WEBHOOK_RECEIVED",
        event_type=event_type,
        payment_intent_id=data.get("id"),
    )

    if event_type == "payment_intent.succeeded":
        await handle_payment_succeeded(db, data)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failed(db, data)
    else:
        logger.debug("WEBHOOK_UNHANDLED_EVENT", event_type=event_type)

    return {"status": "ok"}


async def handle_payment_succeeded(db: Session, payment_intent: dict) -> None:
    """Handle successful payment."""
    payment_intent_id = payment_intent["id"]
    metadata = payment_intent.get("metadata", {})
    action_id = metadata.get("action_id")

    if not action_id:
        logger.warning(
            "PAYMENT_SUCCESS_NO_ACTION_ID",
            payment_intent_id=payment_intent_id,
        )
        return

    action = db.query(PendingAction).filter(PendingAction.action_id == action_id).first()

    if not action:
        logger.warning(
            "PAYMENT_SUCCESS_ACTION_NOT_FOUND",
            action_id=action_id,
            payment_intent_id=payment_intent_id,
        )
        return

    # Mark action as completed
    action.status = PendingActionStatus.COMPLETED
    action.completed_at = datetime.now(UTC)
    action.payment_intent_id = payment_intent_id

    db.commit()

    logger.info(
        "PAYMENT_COMPLETED",
        action_id=action_id,
        payment_intent_id=payment_intent_id,
        amount=payment_intent.get("amount"),
    )


async def handle_payment_failed(db: Session, payment_intent: dict) -> None:
    """Handle failed payment."""
    payment_intent_id = payment_intent["id"]
    metadata = payment_intent.get("metadata", {})
    action_id = metadata.get("action_id")

    if not action_id:
        return

    action = db.query(PendingAction).filter(PendingAction.action_id == action_id).first()

    if action:
        # Reset to pending for retry
        action.status = PendingActionStatus.PENDING
        db.commit()

        logger.warning(
            "PAYMENT_FAILED",
            action_id=action_id,
            payment_intent_id=payment_intent_id,
            error=payment_intent.get("last_payment_error", {}).get("message"),
        )


@router.post("/confirm/{action_id}")
async def confirm_payment_action(
    action_id: str,
    payment_intent_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> dict:
    """
    Manually confirm a payment action after frontend payment completion.

    This endpoint is called by the frontend after Stripe confirms payment
    success on the client side. It verifies with Stripe and updates the action.

    Args:
        action_id: Pending action ID
        payment_intent_id: Stripe payment intent ID
        db: Database session

    Returns:
        Confirmation status
    """
    verify_stripe_configured()

    # Get the action
    action = db.query(PendingAction).filter(PendingAction.action_id == action_id).first()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.status == PendingActionStatus.COMPLETED:
        return {"status": "already_completed", "action_id": action_id}

    try:
        # Verify payment with Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == "succeeded":
            action.status = PendingActionStatus.COMPLETED
            action.completed_at = datetime.now(UTC)
            action.payment_intent_id = payment_intent_id
            db.commit()

            logger.info(
                "PAYMENT_CONFIRMED_MANUALLY",
                action_id=action_id,
                payment_intent_id=payment_intent_id,
            )

            return {
                "status": "completed",
                "action_id": action_id,
                "payment_intent_id": payment_intent_id,
            }
        else:
            return {
                "status": intent.status,
                "action_id": action_id,
                "message": "Payment not yet completed",
            }

    except stripe.error.StripeError as e:
        logger.error("PAYMENT_CONFIRM_ERROR", error=str(e))
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {e!s}") from e
