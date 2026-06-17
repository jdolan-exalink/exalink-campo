from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.weight import WeightRecord
from app.schemas.weight import WeightRecordCreate, WeightRecordResponse
import uuid

router = APIRouter(prefix="/weights", tags=["weights"])


@router.get("", response_model=list[WeightRecordResponse])
async def list_weights(
    animal_id: uuid.UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(WeightRecord).where(WeightRecord.tenant_id == current_user.tenant_id)
    if animal_id:
        q = q.where(WeightRecord.animal_id == animal_id)
    result = await db.execute(q.order_by(WeightRecord.measure_date.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=WeightRecordResponse, status_code=201)
async def create_weight(
    payload: WeightRecordCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    record = WeightRecord(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record
