"""QR Code Generation Endpoint.

POST /checkin/qr/generate - Generate QR code for TV display

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import base64
import io
import os
import secrets
from datetime import datetime, timezone

import qrcode
from backend.database import get_db_dependency
from backend.models.checkin_models import Clinic
from backend.schemas.api.checkin import GenerateQRRequest, GenerateQRResponse
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .helpers import QR_EXPIRY_MINUTES

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - QR"])


@router.post("/qr/generate", response_model=GenerateQRResponse)
def generate_qr(request: GenerateQRRequest, db: Session = Depends(get_db_dependency)):
    """Generate QR code for TV display.

    The QR encodes a URL that patients scan to start check-in.
    QR codes expire after 5 minutes for security.
    """
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail=f"Clinic {request.clinic_id} not found")

    # Generate QR data
    now = datetime.now(UTC)
    expires_at = now.replace(second=0, microsecond=0)
    expires_at = expires_at.replace(minute=expires_at.minute + QR_EXPIRY_MINUTES)

    nonce = secrets.token_urlsafe(8)

    # URL for check-in page (env var for dev/staging/prod flexibility)
    base_url = os.getenv("AURITY_BASE_URL", "https://app.aurity.io")
    qr_url = (
        f"{base_url}/checkin?clinic={request.clinic_id}&t={int(expires_at.timestamp())}&n={nonce}"
    )

    # Generate QR code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    logger.info("QR_GENERATED", clinic_id=request.clinic_id, expires_at=expires_at.isoformat())

    return GenerateQRResponse(
        qr_data=f"data:image/png;base64,{qr_base64}",
        qr_url=qr_url,
        expires_at=expires_at.isoformat(),
    )
