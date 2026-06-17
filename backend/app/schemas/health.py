from pydantic import BaseModel
from datetime import date, datetime
import uuid
from app.models.health import HealthEventType


class HealthEventCreate(BaseModel):
    animal_id: uuid.UUID
    establishment_id: uuid.UUID
    event_type: HealthEventType
    product_name: str
    dose: str | None = None
    route: str | None = None
    event_date: date
    next_date: date | None = None
    vet_name: str | None = None
    cost: float | None = None
    notes: str | None = None


class HealthEventResponse(HealthEventCreate):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
