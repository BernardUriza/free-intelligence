"""Where to reach each account's phones (APNs device tokens)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from fi_runner.auth import Principal
import deps
import push
from deps import get_principal

router = APIRouter()


class DeviceRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200, pattern=r"^[0-9a-fA-F]+$")
    environment: str = Field(default="production", pattern=r"^(production|development)$")


@router.post("/push/devices")
async def push_register(req: DeviceRequest, principal: Principal = Depends(get_principal)) -> dict:
    """A phone says where to reach it. Per account: the shared legacy bearer has no one to tell."""
    if principal.is_legacy_bearer:
        raise HTTPException(status_code=403, detail="push needs an account")
    deps.get_device_store().register(principal.sub, req.token.lower(), req.environment)
    return {"registered": True, "configured": push.is_configured()}


@router.delete("/push/devices/{token}")
async def push_forget(token: str, principal: Principal = Depends(get_principal)) -> dict:
    deps.get_device_store().remove(principal.sub, token.lower())
    return {"registered": False}
