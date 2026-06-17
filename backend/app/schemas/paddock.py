from pydantic import BaseModel
from datetime import datetime
import uuid
from app.models.paddock import PaddockStatus


class PaddockBase(BaseModel):
    name: str
    code: str | None = None
    color: str | None = "#22c55e"
    description: str | None = None
    area_ha: float | None = None
    max_capacity: int | None = None
    status: PaddockStatus = PaddockStatus.EMPTY
    pasture_type: str | None = None
    water_source: bool = True
    notes: str | None = None


class PaddockCreate(PaddockBase):
    establishment_id: uuid.UUID
    polygon: dict | None = None


class PaddockUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    code: str | None = None
    description: str | None = None
    area_ha: float | None = None
    max_capacity: int | None = None
    status: PaddockStatus | None = None
    pasture_type: str | None = None
    water_source: bool | None = None
    notes: str | None = None
    polygon: dict | None = None


class PaddockResponse(PaddockBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    establishment_id: uuid.UUID
    current_load: int
    polygon: dict | None = None
    created_at: datetime
    updated_at: datetime
    animal_count: int = 0
    device_count: int = 0

    model_config = {"from_attributes": True}
