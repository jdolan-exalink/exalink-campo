import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, ForeignKey, UUID, Enum as SAEnum, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import TenantScopedMixin
from app.core.database import Base


class DeviceType(str, enum.Enum):
    GPS_COLLAR = "gps_collar"
    GPS_TAG = "gps_tag"
    SENSOR = "sensor"
    GATEWAY = "gateway"


class Device(TenantScopedMixin, Base):
    __tablename__ = "devices"

    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    animal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    device_uid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    firmware: Mapped[str | None] = mapped_column(String(50))
    sim_iccid: Mapped[str | None] = mapped_column(String(50))
    imei: Mapped[str | None] = mapped_column(String(50))

    battery_pct: Mapped[int | None] = mapped_column(Integer)
    rssi: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Float)
    activity_score: Mapped[int | None] = mapped_column(Integer)

    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_location: Mapped[object | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="devices")
    establishment: Mapped["Establishment"] = relationship("Establishment", back_populates="devices")
    animal: Mapped["Animal | None"] = relationship("Animal", back_populates="device")
    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="device", lazy="noload"
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="device", lazy="noload")
