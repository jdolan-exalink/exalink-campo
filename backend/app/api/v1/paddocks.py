from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.paddock import Paddock
from app.models.establishment import Establishment
from app.models.animal import Animal
from app.models.device import Device
from app.schemas.paddock import PaddockCreate, PaddockUpdate, PaddockResponse
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import shape, mapping
from shapely.prepared import prep
import uuid

router = APIRouter(prefix="/paddocks", tags=["paddocks"])


async def _validate_paddock_inside_establishment(db: AsyncSession, establishment_id, tenant_id, polygon: dict | None):
    if not polygon:
        return None
    result = await db.execute(select(Establishment).where(Establishment.id == establishment_id, Establishment.tenant_id == tenant_id, Establishment.is_active == True))
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(400, "Campo no encontrado")
    if est.boundary is None:
        raise HTTPException(400, "El campo debe tener un poligono antes de crear corrales")
    field_poly = to_shape(est.boundary)
    paddock_poly = shape(polygon)
    if not prep(field_poly).covers(paddock_poly):
        raise HTTPException(400, "El corral debe quedar completamente dentro del campo")
    return paddock_poly


def _serialize(paddock: Paddock, animal_count: int = 0, device_count: int = 0) -> PaddockResponse:
    polygon = None
    if paddock.polygon is not None:
        polygon = mapping(to_shape(paddock.polygon))
    return PaddockResponse(
        id=paddock.id,
        tenant_id=paddock.tenant_id,
        establishment_id=paddock.establishment_id,
        name=paddock.name,
        code=paddock.code,
        color=paddock.color,
        description=paddock.description,
        area_ha=paddock.area_ha,
        max_capacity=paddock.max_capacity,
        current_load=paddock.current_load,
        status=paddock.status,
        pasture_type=paddock.pasture_type,
        water_source=paddock.water_source,
        notes=paddock.notes,
        polygon=polygon,
        created_at=paddock.created_at,
        updated_at=paddock.updated_at,
        animal_count=animal_count,
        device_count=device_count,
    )


@router.get("", response_model=list[PaddockResponse])
async def list_paddocks(
    establishment_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Paddock).where(Paddock.tenant_id == current_user.tenant_id, Paddock.is_active == True)
    if establishment_id:
        q = q.where(Paddock.establishment_id == establishment_id)
    result = await db.execute(q.order_by(Paddock.name))
    paddocks = result.scalars().all()

    responses = []
    for p in paddocks:
        animal_count_result = await db.execute(
            select(func.count(Animal.id)).where(Animal.paddock_id == p.id, Animal.status == "active")
        )
        device_count_result = await db.execute(
            select(func.count(Device.id))
            .select_from(Animal)
            .join(Device, Device.animal_id == Animal.id)
            .where(Animal.paddock_id == p.id, Animal.status == "active", Device.is_active == True)
        )
        responses.append(_serialize(p, animal_count_result.scalar() or 0, device_count_result.scalar() or 0))
    return responses


@router.post("", response_model=PaddockResponse, status_code=201)
async def create_paddock(
    payload: PaddockCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    data = payload.model_dump(exclude={"polygon"})
    paddock_poly = await _validate_paddock_inside_establishment(db, payload.establishment_id, current_user.tenant_id, payload.polygon)
    paddock = Paddock(**data, tenant_id=current_user.tenant_id, created_by=current_user.id)
    if paddock_poly is not None:
        paddock.polygon = from_shape(paddock_poly, srid=4326)
    db.add(paddock)
    await db.flush()
    await db.refresh(paddock)
    return _serialize(paddock)


@router.get("/{paddock_id}", response_model=PaddockResponse)
async def get_paddock(
    paddock_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paddock).where(Paddock.id == paddock_id, Paddock.tenant_id == current_user.tenant_id)
    )
    paddock = result.scalar_one_or_none()
    if not paddock:
        raise HTTPException(404, "Potrero no encontrado")
    animal_count_result = await db.execute(
        select(func.count(Animal.id)).where(Animal.paddock_id == paddock_id, Animal.status == "active")
    )
    device_count_result = await db.execute(
        select(func.count(Device.id))
        .select_from(Animal)
        .join(Device, Device.animal_id == Animal.id)
        .where(Animal.paddock_id == paddock_id, Animal.status == "active", Device.is_active == True)
    )
    return _serialize(paddock, animal_count_result.scalar() or 0, device_count_result.scalar() or 0)


@router.put("/{paddock_id}", response_model=PaddockResponse)
async def update_paddock(
    paddock_id: uuid.UUID,
    payload: PaddockUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paddock).where(Paddock.id == paddock_id, Paddock.tenant_id == current_user.tenant_id)
    )
    paddock = result.scalar_one_or_none()
    if not paddock:
        raise HTTPException(404, "Potrero no encontrado")

    updates = payload.model_dump(exclude_unset=True, exclude={"polygon"})
    for k, v in updates.items():
        setattr(paddock, k, v)
    if payload.polygon is not None:
        paddock_poly = await _validate_paddock_inside_establishment(db, paddock.establishment_id, current_user.tenant_id, payload.polygon)
        paddock.polygon = from_shape(paddock_poly, srid=4326) if paddock_poly is not None else None
    paddock.updated_by = current_user.id
    await db.flush()
    await db.refresh(paddock)
    return _serialize(paddock)


@router.delete("/{paddock_id}", status_code=204)
async def delete_paddock(
    paddock_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Paddock).where(Paddock.id == paddock_id, Paddock.tenant_id == current_user.tenant_id)
    )
    paddock = result.scalar_one_or_none()
    if not paddock:
        raise HTTPException(404, "Potrero no encontrado")
    paddock.is_active = False
    await db.flush()
