from pydantic import BaseModel
from datetime import datetime
import uuid


class EstablishmentBase(BaseModel):
    name: str
    code: str | None = None
    color: str | None = "#3b82f6"
    address: str | None = None
    province: str | None = None
    municipality: str | None = None
    total_area_ha: float | None = None
    renspa: str | None = None
    senasa_code: str | None = None
    notes: str | None = None


class EstablishmentCreate(EstablishmentBase):
    lat: float | None = None
    lon: float | None = None
    boundary: dict | None = None


class EstablishmentUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    code: str | None = None
    address: str | None = None
    province: str | None = None
    municipality: str | None = None
    total_area_ha: float | None = None
    renspa: str | None = None
    senasa_code: str | None = None
    notes: str | None = None
    lat: float | None = None
    lon: float | None = None
    boundary: dict | None = None
    is_active: bool | None = None


class EstablishmentResponse(EstablishmentBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool
    lat: float | None = None
    lon: float | None = None
    boundary: dict | None = None
    created_at: datetime
    paddock_count: int = 0
    animal_count: int = 0
    device_count: int = 0

    model_config = {"from_attributes": True}
