import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, UUID, Enum as SAEnum, DateTime, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class AlertType(str, enum.Enum):
    OUTSIDE_GEOFENCE = "outside_geofence"
    OUTSIDE_FIELD = "outside_field"
    IMMOBILE = "immobile"
    LOW_BATTERY = "low_battery"
    DEVICE_OFFLINE = "device_offline"
    PROLONGED_DISCONNECT = "prolonged_disconnect"
    ABNORMAL_ACTIVITY = "abnormal_activity"
    POSSIBLE_HEAT = "possible_heat"
    POSSIBLE_BIRTH = "possible_birth"
    VACCINE_DUE = "vaccine_due"
    TEMPERATURE_LOW = "temperature_low"
    TEMPERATURE_HIGH = "temperature_high"
    MANUAL = "manual"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# Alert types that can be configured by the user via AlertConfig
CONFIGURABLE_ALERT_TYPES = {
    AlertType.TEMPERATURE_LOW,
    AlertType.TEMPERATURE_HIGH,
    AlertType.LOW_BATTERY,
    AlertType.DEVICE_OFFLINE,
    AlertType.PROLONGED_DISCONNECT,
    AlertType.OUTSIDE_GEOFENCE,
    AlertType.OUTSIDE_FIELD,
}


class Alert(TenantScopedMixin, Base):
    __tablename__ = "alerts"

    establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    animal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=AlertStatus.OPEN, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="alerts")
    animal: Mapped["Animal | None"] = relationship("Animal", back_populates="alerts")
    device: Mapped["Device | None"] = relationship("Device", back_populates="alerts")
