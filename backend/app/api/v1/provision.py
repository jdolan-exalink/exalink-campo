"""
Device provisioning API.

Flow:
  NOC creates device in inventory (no tenant) → device shipped to client
  → device enters pairing mode (shows XXXX-XXXX code on display + QR)
  → client user scans QR or types code at /provision/{code}
  → POST /provision/{code} claims device for user's tenant
  → device polls gateway sync and receives is_provisioned=true

Self-reset (button 10s on device):
  → device calls DELETE /provision/{code} with its own device_uid
  → backend marks device as unprovisioned
  → device wipes NVS and reboots into pairing mode
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.device import Device
from app.models.establishment import Establishment
from app.models.user import User
from app.schemas.device import (
    ProvisionLookupResponse,
    ProvisionClaimRequest,
    ProvisionResetRequest,
)

router = APIRouter(prefix="/provision", tags=["provision"])
logger = logging.getLogger("provision")


def _normalize(code: str) -> str:
    return code.upper().replace(" ", "").replace("_", "-")


@router.get("/{code}", response_model=ProvisionLookupResponse)
async def lookup_provision(code: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Public — check if a provision code exists and whether it's available."""
    normalized = _normalize(code)
    device = await db.scalar(
        select(Device).where(Device.provision_code == normalized)
    )
    if not device:
        logger.info(
            "provision.lookup code=%s ip=%s result=not_found",
            normalized,
            request.client.host if request.client else "-",
        )
        raise HTTPException(404, "Código no encontrado")
    return ProvisionLookupResponse(
        provision_code=device.provision_code,
        device_uid=device.device_uid,
        device_type=device.device_type,
        firmware=device.firmware,
        is_provisioned=device.is_provisioned,
    )


@router.post("/{code}")
async def claim_device(
    code: str,
    payload: ProvisionClaimRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Claim a device for the authenticated user's tenant."""
    normalized = _normalize(code)
    device = await db.scalar(
        select(Device).where(Device.provision_code == normalized)
    )
    ip = request.client.host if request.client else "-"
    ua = request.headers.get("user-agent", "-")

    if not device:
        logger.info("provision.claim code=%s user=%s ip=%s ua=%s result=not_found",
                    normalized, current_user.email, ip, ua)
        raise HTTPException(404, "Código no encontrado")
    if device.is_provisioned:
        logger.info("provision.claim code=%s user=%s ip=%s ua=%s result=already_paired device_uid=%s",
                    normalized, current_user.email, ip, ua, device.device_uid)
        raise HTTPException(409, "Dispositivo ya registrado. Contacte al NOC para resetearlo.")

    est = await db.scalar(
        select(Establishment).where(
            Establishment.id == payload.establishment_id,
            Establishment.tenant_id == current_user.tenant_id,
            Establishment.is_active == True,
        )
    )
    if not est:
        logger.info("provision.claim code=%s user=%s ip=%s result=establishment_not_found",
                    normalized, current_user.email, ip)
        raise HTTPException(404, "Establecimiento no encontrado")

    device.tenant_id = current_user.tenant_id
    device.establishment_id = payload.establishment_id
    if payload.name:
        device.name = payload.name
    device.is_provisioned = True
    device.provisioned_at = datetime.now(timezone.utc)
    device.provisioned_by = current_user.id
    device.updated_by = current_user.id

    await db.flush()
    logger.info("provision.claim OK code=%s user=%s ip=%s device_uid=%s establishment=%s",
                normalized, current_user.email, ip, device.device_uid, est.id)
    return {
        "ok": True,
        "message": "Dispositivo registrado exitosamente",
        "device_uid": device.device_uid,
        "device_type": device.device_type,
        "name": device.name,
    }


@router.delete("/{code}")
async def reset_provision(
    code: str,
    payload: ProvisionResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Device self-reset: called by the device before factory reset.
    No user auth — device proves ownership by knowing its own device_uid.
    """
    normalized = _normalize(code)
    device = await db.scalar(
        select(Device).where(Device.provision_code == normalized)
    )
    ip = request.client.host if request.client else "-"
    ua = request.headers.get("user-agent", "-")

    if not device:
        logger.info("provision.reset code=%s ip=%s ua=%s result=not_found", normalized, ip, ua)
        raise HTTPException(404, "Código no encontrado")
    if device.device_uid != payload.device_uid:
        logger.warning("provision.reset code=%s ip=%s ua=%s result=forbidden device_uid=%s expected=%s",
                       normalized, ip, ua, payload.device_uid, device.device_uid)
        raise HTTPException(403, "No autorizado")

    device.tenant_id = None
    device.establishment_id = None
    device.is_provisioned = False
    device.provisioned_at = None
    device.provisioned_by = None

    await db.flush()
    logger.info("provision.reset OK code=%s device_uid=%s ip=%s", normalized, device.device_uid, ip)
    return {"ok": True, "message": "Dispositivo desregistrado. Listo para re-provisionar."}
