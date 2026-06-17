from pydantic import BaseModel
from datetime import date, datetime
import uuid


class WeightRecordCreate(BaseModel):
    animal_id: uuid.UUID
    weight_kg: float
    measure_date: date
    method: str | None = None
    device_uid: str | None = None
    notes: str | None = None


class WeightRecordResponse(WeightRecordCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    daily_gain: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
