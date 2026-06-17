from pydantic import BaseModel
from datetime import datetime
import uuid
from app.models.alert import AlertType, AlertSeverity, AlertStatus


class AlertCreate(BaseModel):
    establishment_id: uuid.UUID | None = None
    animal_id: uuid.UUID | None = None
    device_id: uuid.UUID | None = None
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str | None = None


class AlertResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    establishment_id: uuid.UUID | None
    animal_id: uuid.UUID | None
    device_id: uuid.UUID | None
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str | None
    created_at: datetime
    resolved_at: datetime | None
    animal_ear_tag: str | None = None
    device_uid: str | None = None

    model_config = {"from_attributes": True}
