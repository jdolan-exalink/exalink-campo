from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import require_superadmin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.animal import Animal, AnimalStatus
from app.models.device import Device
from app.models.alert import Alert, AlertStatus, AlertSeverity
from app.schemas.device import NocDeviceCreate
import uuid
import re

router = APIRouter(prefix="/noc", tags=["noc"])


def _provision_code_from_uid(device_uid: str) -> str:
    """Derive XXXX-XXXX provision code from Heltec chip ID (last 8 hex chars)."""
    clean = re.sub(r"[^0-9A-Fa-f]", "", device_uid)
    hex8 = clean[-8:].upper().zfill(8)
    return f"{hex8[:4]}-{hex8[4:]}"


@router.get("/overview")
async def noc_overview(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    tenants_result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    tenants = tenants_result.scalars().all()

    overview = []
    for tenant in tenants:
        animals = await db.scalar(
            select(func.count(Animal.id)).where(
                Animal.tenant_id == tenant.id, Animal.status == AnimalStatus.ACTIVE
            )
        )
        devices_online = await db.scalar(
            select(func.count(Device.id)).where(
                Device.tenant_id == tenant.id, Device.is_active == True, Device.is_online == True
            )
        )
        devices_total = await db.scalar(
            select(func.count(Device.id)).where(
                Device.tenant_id == tenant.id, Device.is_active == True
            )
        )
        open_critical = await db.scalar(
            select(func.count(Alert.id)).where(
                Alert.tenant_id == tenant.id,
                Alert.status == AlertStatus.OPEN,
                Alert.severity == AlertSeverity.CRITICAL,
            )
        )
        overview.append({
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "tenant_slug": tenant.slug,
            "plan": tenant.plan,
            "animals": animals or 0,
            "devices_online": devices_online or 0,
            "devices_total": devices_total or 0,
            "critical_alerts": open_critical or 0,
        })
    return {"tenants": overview, "total_tenants": len(overview)}


@router.post("/devices", status_code=201)
async def noc_create_device(
    payload: NocDeviceCreate,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """Create a device in inventory (no tenant). Used before shipping to client."""
    existing = await db.scalar(
        select(Device).where(Device.device_uid == payload.device_uid)
    )
    if existing:
        raise HTTPException(409, f"device_uid '{payload.device_uid}' ya existe")

    code = payload.provision_code or _provision_code_from_uid(payload.device_uid)
    code = code.upper()

    code_conflict = await db.scalar(
        select(Device).where(Device.provision_code == code)
    )
    if code_conflict:
        raise HTTPException(409, f"provision_code '{code}' ya está en uso")

    device = Device(
        device_uid=payload.device_uid,
        device_type=payload.device_type,
        name=payload.name,
        firmware=payload.firmware,
        provision_code=code,
        is_provisioned=False,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(device)
    await db.flush()
    return {
        "id": str(device.id),
        "device_uid": device.device_uid,
        "device_type": device.device_type,
        "provision_code": device.provision_code,
        "is_provisioned": device.is_provisioned,
    }


@router.post("/devices/{device_id}/reset-provision")
async def noc_reset_provision(
    device_id: uuid.UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """NOC reset: un-provision a device so it can be re-registered."""
    device = await db.scalar(select(Device).where(Device.id == device_id))
    if not device:
        raise HTTPException(404, "Dispositivo no encontrado")

    device.tenant_id = None
    device.establishment_id = None
    device.is_provisioned = False
    device.provisioned_at = None
    device.provisioned_by = None
    device.updated_by = current_user.id

    await db.flush()
    return {
        "ok": True,
        "provision_code": device.provision_code,
        "message": "Dispositivo listo para re-provisionar.",
    }


@router.get("/devices")
async def noc_devices(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device)
        .where(Device.is_active == True)
        .order_by(Device.is_online.asc(), Device.last_seen.asc())
        .limit(200)
    )
    devices = result.scalars().all()
    return [
        {
            "device_uid": d.device_uid,
            "device_type": d.device_type.value,
            "tenant_id": str(d.tenant_id),
            "is_online": d.is_online,
            "battery_pct": d.battery_pct,
            "firmware": d.firmware,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        }
        for d in devices
    ]
