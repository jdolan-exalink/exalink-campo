from pydantic import BaseModel
from datetime import date, datetime
import uuid
from app.models.reproduction import ReproductionEventType


class ReproductionEventCreate(BaseModel):
    animal_id: uuid.UUID
    event_type: ReproductionEventType
    event_date: date
    expected_birth_date: date | None = None
    is_pregnant: bool | None = None
    result: str | None = None
    semen_batch: str | None = None
    bull_id: uuid.UUID | None = None
    vet_name: str | None = None
    notes: str | None = None


class ReproductionEventResponse(ReproductionEventCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
