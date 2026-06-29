from pydantic import BaseModel, field_validator
from datetime import datetime
import uuid
from app.models.device import DeviceType


class DeviceBase(BaseModel):
    device_uid: str
    device_type: DeviceType
    name: str | None = None
    firmware: str | None = None
    sim_iccid: str | None = None
    imei: str | None = None
    notes: str | None = None


class DeviceCreate(DeviceBase):
    establishment_id: uuid.UUID
    animal_id: uuid.UUID | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    firmware: str | None = None
    animal_id: uuid.UUID | None = None
    notes: str | None = None
    is_active: bool | None = None


class DeviceResponse(DeviceBase):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    establishment_id: uuid.UUID | None
    animal_id: uuid.UUID | None
    battery_pct: int | None
    rssi: int | None
    temperature: float | None
    activity_score: int | None
    is_online: bool
    last_seen: datetime | None
    last_lat: float | None = None
    last_lon: float | None = None
    is_active: bool
    provision_code: str | None = None
    is_provisioned: bool = False
    created_at: datetime
    animal_ear_tag: str | None = None

    model_config = {"from_attributes": True}


# ── NOC inventory creation ─────────────────────────────────────────────────────

class NocDeviceCreate(BaseModel):
    device_uid: str                    # Heltec chip ID, e.g. "A4CF12ABCDEF"
    device_type: DeviceType
    name: str | None = None
    firmware: str | None = None
    provision_code: str | None = None  # auto-derived from device_uid if omitted


# ── Provisioning ───────────────────────────────────────────────────────────────

class ProvisionLookupResponse(BaseModel):
    provision_code: str
    device_uid: str
    device_type: str
    firmware: str | None
    is_provisioned: bool


class ProvisionClaimRequest(BaseModel):
    establishment_id: uuid.UUID
    name: str | None = None


class ProvisionResetRequest(BaseModel):
    device_uid: str  # device proves ownership


# ── MQTT ──────────────────────────────────────────────────────────────────────

class MQTTLocationPayload(BaseModel):
    device_id: str
    lat: float
    lon: float
    battery: int | None = None
    rssi: int | None = None
    temperature: float | None = None
    activity_score: int | None = None
    speed: float | None = None
    altitude: float | None = None
    timestamp: datetime | None = None
