from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional
import uuid
from app.models.animal import AnimalSex, AnimalStatus, AnimalCategory


class AnimalBase(BaseModel):
    ear_tag: str
    rfid: str | None = None
    name: str | None = None
    breed: str | None = None
    sex: AnimalSex
    category: AnimalCategory | None = None
    status: AnimalStatus = AnimalStatus.ACTIVE
    birth_date: date | None = None
    color: str | None = None
    weight_kg: float | None = None
    paddock_id: uuid.UUID | None = None
    herd_id: uuid.UUID | None = None
    notes: str | None = None


class AnimalCreate(AnimalBase):
    establishment_id: uuid.UUID


class AnimalUpdate(BaseModel):
    ear_tag: str | None = None
    rfid: str | None = None
    name: str | None = None
    breed: str | None = None
    sex: AnimalSex | None = None
    category: AnimalCategory | None = None
    status: AnimalStatus | None = None
    birth_date: date | None = None
    color: str | None = None
    weight_kg: float | None = None
    paddock_id: uuid.UUID | None = None
    herd_id: uuid.UUID | None = None
    notes: str | None = None


class AnimalResponse(AnimalBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    establishment_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    paddock_name: str | None = None
    herd_name: str | None = None
    has_device: bool = False
    device_uid: str | None = None
    last_lat: float | None = None
    last_lon: float | None = None

    model_config = {"from_attributes": True}


class AnimalListResponse(BaseModel):
    items: list[AnimalResponse]
    total: int
    page: int
    page_size: int
    pages: int
