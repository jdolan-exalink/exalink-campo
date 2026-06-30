from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from app.models.alert import AlertType, AlertSeverity


class AlertConfigBase(BaseModel):
    alert_type: AlertType
    enabled: bool = True
    severity: AlertSeverity = AlertSeverity.WARNING
    threshold_value: float | None = None
    threshold_min: float | None = None
    threshold_max: float | None = None
    repeat_interval_minutes: int = Field(default=0, ge=0)
    browser_notify: bool = True
    name: str | None = None
    notes: str | None = None
    establishment_id: uuid.UUID | None = None


class AlertConfigCreate(AlertConfigBase):
    pass


class AlertConfigUpdate(BaseModel):
    enabled: bool | None = None
    severity: AlertSeverity | None = None
    threshold_value: float | None = None
    threshold_min: float | None = None
    threshold_max: float | None = None
    repeat_interval_minutes: int | None = Field(default=None, ge=0)
    browser_notify: bool | None = None
    name: str | None = None
    notes: str | None = None


class AlertConfigResponse(AlertConfigBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
