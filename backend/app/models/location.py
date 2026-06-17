import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, UUID, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import UUIDMixin
from app.core.database import Base


class Location(UUIDMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_locations_device_timestamp", "device_id", "timestamp"),
        Index("ix_locations_animal_timestamp", "animal_id", "timestamp"),
        Index("ix_locations_tenant_timestamp", "tenant_id", "timestamp"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    animal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="SET NULL"), nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    point: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    battery_pct: Mapped[int | None] = mapped_column(Integer)
    rssi: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[float | None] = mapped_column(Float)
    activity_score: Mapped[int | None] = mapped_column(Integer)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    altitude_m: Mapped[float | None] = mapped_column(Float)

    device: Mapped["Device"] = relationship("Device", back_populates="locations")
    animal: Mapped["Animal | None"] = relationship("Animal", back_populates="locations")
