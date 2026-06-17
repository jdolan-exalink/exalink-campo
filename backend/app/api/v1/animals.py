from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.animal import Animal, AnimalStatus
from app.models.device import Device
from app.models.paddock import Paddock
from app.models.herd import Herd
from app.models.location import Location
from app.schemas.animal import AnimalCreate, AnimalUpdate, AnimalResponse, AnimalListResponse
from geoalchemy2.shape import to_shape
import uuid
import math

router = APIRouter(prefix="/animals", tags=["animals"])


def _build_response(animal: Animal) -> AnimalResponse:
    data = AnimalResponse(
        id=animal.id,
        tenant_id=animal.tenant_id,
        establishment_id=animal.establishment_id,
        paddock_id=animal.paddock_id,
        herd_id=animal.herd_id,
        ear_tag=animal.ear_tag,
        rfid=animal.rfid,
        name=animal.name,
        breed=animal.breed,
        sex=animal.sex,
        category=animal.category,
        status=animal.status,
        birth_date=animal.birth_date,
        color=animal.color,
        weight_kg=animal.weight_kg,
        notes=animal.notes,
        created_at=animal.created_at,
        updated_at=animal.updated_at,
        paddock_name=animal.paddock.name if animal.paddock else None,
        herd_name=animal.herd.name if animal.herd else None,
        has_device=animal.device is not None,
        device_uid=animal.device.device_uid if animal.device else None,
    )
    if animal.device and animal.device.last_location:
        pt = to_shape(animal.device.last_location)
        data.last_lon = pt.x
        data.last_lat = pt.y
    return data


@router.get("", response_model=AnimalListResponse)
async def list_animals(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    establishment_id: uuid.UUID | None = None,
    paddock_id: uuid.UUID | None = None,
    status: AnimalStatus | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Animal)
        .options(
            selectinload(Animal.paddock),
            selectinload(Animal.herd),
            selectinload(Animal.device),
        )
        .where(Animal.tenant_id == current_user.tenant_id)
    )
    if establishment_id:
        q = q.where(Animal.establishment_id == establishment_id)
    if paddock_id:
        q = q.where(Animal.paddock_id == paddock_id)
    if status:
        q = q.where(Animal.status == status)
    if search:
        q = q.where(Animal.ear_tag.ilike(f"%{search}%") | Animal.name.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar()

    q = q.offset((page - 1) * page_size).limit(page_size).order_by(Animal.ear_tag)
    result = await db.execute(q)
    animals = result.scalars().all()

    return AnimalListResponse(
        items=[_build_response(a) for a in animals],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=AnimalResponse, status_code=201)
async def create_animal(
    payload: AnimalCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    animal = Animal(
        **payload.model_dump(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
    )
    db.add(animal)
    await db.flush()
    await db.refresh(animal)

    result = await db.execute(
        select(Animal)
        .options(selectinload(Animal.paddock), selectinload(Animal.herd), selectinload(Animal.device))
        .where(Animal.id == animal.id)
    )
    return _build_response(result.scalar_one())


@router.get("/{animal_id}", response_model=AnimalResponse)
async def get_animal(
    animal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Animal)
        .options(selectinload(Animal.paddock), selectinload(Animal.herd), selectinload(Animal.device))
        .where(Animal.id == animal_id, Animal.tenant_id == current_user.tenant_id)
    )
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(404, "Animal no encontrado")
    return _build_response(animal)


@router.put("/{animal_id}", response_model=AnimalResponse)
async def update_animal(
    animal_id: uuid.UUID,
    payload: AnimalUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Animal).where(Animal.id == animal_id, Animal.tenant_id == current_user.tenant_id)
    )
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(404, "Animal no encontrado")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(animal, field, value)
    animal.updated_by = current_user.id
    await db.flush()

    result = await db.execute(
        select(Animal)
        .options(selectinload(Animal.paddock), selectinload(Animal.herd), selectinload(Animal.device))
        .where(Animal.id == animal_id)
    )
    return _build_response(result.scalar_one())


@router.delete("/{animal_id}", status_code=204)
async def delete_animal(
    animal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Animal).where(Animal.id == animal_id, Animal.tenant_id == current_user.tenant_id)
    )
    animal = result.scalar_one_or_none()
    if not animal:
        raise HTTPException(404, "Animal no encontrado")
    await db.delete(animal)


@router.get("/{animal_id}/track")
async def get_animal_track(
    animal_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Location)
        .where(Location.animal_id == animal_id, Location.tenant_id == current_user.tenant_id)
        .order_by(Location.timestamp.desc())
        .limit(limit)
    )
    locations = result.scalars().all()
    track = []
    for loc in locations:
        pt = to_shape(loc.point)
        track.append({
            "timestamp": loc.timestamp.isoformat(),
            "lat": pt.y,
            "lon": pt.x,
            "battery_pct": loc.battery_pct,
            "activity_score": loc.activity_score,
            "temperature": loc.temperature,
        })
    return {"animal_id": str(animal_id), "track": track}
