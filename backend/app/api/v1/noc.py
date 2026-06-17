from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import require_superadmin
from app.models.user import User
from app.models.tenant import Tenant
from app.models.animal import Animal, AnimalStatus
from app.models.device import Device
from app.models.alert import Alert, AlertStatus, AlertSeverity

router = APIRouter(prefix="/noc", tags=["noc"])


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
