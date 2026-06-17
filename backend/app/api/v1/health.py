from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.health import HealthEvent
from app.schemas.health import HealthEventCreate, HealthEventResponse
import uuid

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=list[HealthEventResponse])
async def list_health_events(
    animal_id: uuid.UUID | None = None,
    establishment_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(HealthEvent).where(HealthEvent.tenant_id == current_user.tenant_id)
    if animal_id:
        q = q.where(HealthEvent.animal_id == animal_id)
    if establishment_id:
        q = q.where(HealthEvent.establishment_id == establishment_id)
    result = await db.execute(q.order_by(HealthEvent.event_date.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=HealthEventResponse, status_code=201)
async def create_health_event(
    payload: HealthEventCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    event = HealthEvent(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_health_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthEvent).where(HealthEvent.id == event_id, HealthEvent.tenant_id == current_user.tenant_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Evento no encontrado")
    await db.delete(event)
