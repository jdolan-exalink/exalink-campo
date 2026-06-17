from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.device import Device
from app.models.location import Location
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse
from geoalchemy2.shape import to_shape
import uuid

router = APIRouter(prefix="/devices", tags=["devices"])


def _serialize(device: Device) -> DeviceResponse:
    last_lat = last_lon = None
    if device.last_location:
        pt = to_shape(device.last_location)
        last_lon = pt.x
        last_lat = pt.y
    return DeviceResponse(
        id=device.id,
        tenant_id=device.tenant_id,
        establishment_id=device.establishment_id,
        animal_id=device.animal_id,
        device_uid=device.device_uid,
        device_type=device.device_type,
        name=device.name,
        firmware=device.firmware,
        sim_iccid=device.sim_iccid,
        imei=device.imei,
        battery_pct=device.battery_pct,
        rssi=device.rssi,
        temperature=device.temperature,
        activity_score=device.activity_score,
        is_online=device.is_online,
        last_seen=device.last_seen,
        last_lat=last_lat,
        last_lon=last_lon,
        is_active=device.is_active,
        notes=device.notes,
        created_at=device.created_at,
        animal_ear_tag=device.animal.ear_tag if device.animal else None,
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    establishment_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Device)
        .options(selectinload(Device.animal))
        .where(Device.tenant_id == current_user.tenant_id, Device.is_active == True)
    )
    if establishment_id:
        q = q.where(Device.establishment_id == establishment_id)
    result = await db.execute(q.order_by(Device.device_uid))
    return [_serialize(d) for d in result.scalars().all()]


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    payload: DeviceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    device = Device(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(device)
    await db.flush()
    result = await db.execute(
        select(Device).options(selectinload(Device.animal)).where(Device.id == device.id)
    )
    return _serialize(result.scalar_one())


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device)
        .options(selectinload(Device.animal))
        .where(Device.id == device_id, Device.tenant_id == current_user.tenant_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Dispositivo no encontrado")
    return _serialize(device)


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: uuid.UUID,
    payload: DeviceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.tenant_id == current_user.tenant_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Dispositivo no encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(device, k, v)
    device.updated_by = current_user.id
    await db.flush()
    result = await db.execute(
        select(Device).options(selectinload(Device.animal)).where(Device.id == device_id)
    )
    return _serialize(result.scalar_one())


@router.get("/{device_id}/track")
async def get_device_track(
    device_id: uuid.UUID,
    limit: int = Query(200, ge=1, le=2000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Location)
        .where(Location.device_id == device_id, Location.tenant_id == current_user.tenant_id)
        .order_by(Location.timestamp.desc())
        .limit(limit)
    )
    locs = result.scalars().all()
    return [
        {
            "timestamp": loc.timestamp.isoformat(),
            "lat": to_shape(loc.point).y,
            "lon": to_shape(loc.point).x,
            "battery_pct": loc.battery_pct,
            "activity_score": loc.activity_score,
        }
        for loc in locs
    ]
