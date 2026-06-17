from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.establishment import Establishment
from app.models.paddock import Paddock
from app.models.animal import Animal, AnimalStatus
from app.models.device import Device
from app.schemas.establishment import EstablishmentCreate, EstablishmentUpdate, EstablishmentResponse
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, shape, mapping
import uuid

router = APIRouter(prefix="/establishments", tags=["establishments"])


async def _serialize(establishment: Establishment, db: AsyncSession) -> EstablishmentResponse:
    lat = lon = None
    boundary = None
    if establishment.location:
        pt = to_shape(establishment.location)
        lon = pt.x
        lat = pt.y
    if establishment.boundary:
        boundary = mapping(to_shape(establishment.boundary))

    paddock_count = await db.scalar(
        select(func.count(Paddock.id)).where(Paddock.establishment_id == establishment.id, Paddock.is_active == True)
    )
    animal_count = await db.scalar(
        select(func.count(Animal.id)).where(Animal.establishment_id == establishment.id, Animal.status == AnimalStatus.ACTIVE)
    )
    device_count = await db.scalar(
        select(func.count(Device.id)).where(Device.establishment_id == establishment.id, Device.is_active == True)
    )
    return EstablishmentResponse(
        id=establishment.id,
        tenant_id=establishment.tenant_id,
        name=establishment.name,
        code=establishment.code,
        color=establishment.color,
        address=establishment.address,
        province=establishment.province,
        municipality=establishment.municipality,
        total_area_ha=establishment.total_area_ha,
        renspa=establishment.renspa,
        senasa_code=establishment.senasa_code,
        notes=establishment.notes,
        is_active=establishment.is_active,
        lat=lat,
        lon=lon,
        boundary=boundary,
        created_at=establishment.created_at,
        paddock_count=paddock_count or 0,
        animal_count=animal_count or 0,
        device_count=device_count or 0,
    )


@router.get("", response_model=list[EstablishmentResponse])
async def list_establishments(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Establishment).where(
            Establishment.tenant_id == current_user.tenant_id, Establishment.is_active == True
        ).order_by(Establishment.name)
    )
    return [await _serialize(e, db) for e in result.scalars().all()]


@router.post("", response_model=EstablishmentResponse, status_code=201)
async def create_establishment(
    payload: EstablishmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude={"lat", "lon", "boundary"})
    est = Establishment(**data, tenant_id=current_user.tenant_id, created_by=current_user.id)
    if payload.lat is not None and payload.lon is not None:
        est.location = from_shape(Point(payload.lon, payload.lat), srid=4326)
    if payload.boundary is not None:
        est.boundary = from_shape(shape(payload.boundary), srid=4326) if payload.boundary else None
    db.add(est)
    await db.flush()
    await db.refresh(est)
    return await _serialize(est, db)


@router.get("/{establishment_id}", response_model=EstablishmentResponse)
async def get_establishment(
    establishment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Establishment).where(
            Establishment.id == establishment_id, Establishment.tenant_id == current_user.tenant_id
        )
    )
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(404, "Establecimiento no encontrado")
    return await _serialize(est, db)


@router.put("/{establishment_id}", response_model=EstablishmentResponse)
async def update_establishment(
    establishment_id: uuid.UUID,
    payload: EstablishmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Establishment).where(
            Establishment.id == establishment_id, Establishment.tenant_id == current_user.tenant_id
        )
    )
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(404, "Establecimiento no encontrado")
    updates = payload.model_dump(exclude_unset=True, exclude={"lat", "lon", "boundary"})
    for k, v in updates.items():
        setattr(est, k, v)
    if payload.lat is not None and payload.lon is not None:
        est.location = from_shape(Point(payload.lon, payload.lat), srid=4326)
    if payload.boundary is not None:
        est.boundary = from_shape(shape(payload.boundary), srid=4326) if payload.boundary else None
    est.updated_by = current_user.id
    await db.flush()
    await db.refresh(est)
    return await _serialize(est, db)


@router.delete("/{establishment_id}", status_code=204)
async def delete_establishment(
    establishment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Establishment).where(
            Establishment.id == establishment_id, Establishment.tenant_id == current_user.tenant_id
        )
    )
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(404, "Campo no encontrado")
    est.is_active = False
    est.updated_by = current_user.id
    paddocks_result = await db.execute(
        select(Paddock).where(Paddock.establishment_id == establishment_id, Paddock.is_active == True)
    )
    for paddock in paddocks_result.scalars().all():
        paddock.is_active = False
        paddock.updated_by = current_user.id
    await db.flush()
