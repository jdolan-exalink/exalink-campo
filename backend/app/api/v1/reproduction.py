from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.reproduction import ReproductionEvent
from app.schemas.reproduction import ReproductionEventCreate, ReproductionEventResponse
import uuid

router = APIRouter(prefix="/reproduction", tags=["reproduction"])


@router.get("", response_model=list[ReproductionEventResponse])
async def list_events(
    animal_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(ReproductionEvent).where(ReproductionEvent.tenant_id == current_user.tenant_id)
    if animal_id:
        q = q.where(ReproductionEvent.animal_id == animal_id)
    result = await db.execute(q.order_by(ReproductionEvent.event_date.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ReproductionEventResponse, status_code=201)
async def create_event(
    payload: ReproductionEventCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    event = ReproductionEvent(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event
