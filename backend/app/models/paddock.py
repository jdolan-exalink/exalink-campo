import enum
import uuid
from sqlalchemy import String, Float, Text, ForeignKey, UUID, Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import TenantScopedMixin
from app.core.database import Base


class PaddockStatus(str, enum.Enum):
    OCCUPIED = "occupied"
    EMPTY = "empty"
    RESTING = "resting"
    MAINTENANCE = "maintenance"


class Paddock(TenantScopedMixin, Base):
    __tablename__ = "paddocks"

    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(20), default="#22c55e")
    description: Mapped[str | None] = mapped_column(Text)
    area_ha: Mapped[float | None] = mapped_column(Float)
    max_capacity: Mapped[int | None] = mapped_column(Integer)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PaddockStatus] = mapped_column(SAEnum(PaddockStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=PaddockStatus.EMPTY)
    polygon: Mapped[object | None] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    pasture_type: Mapped[str | None] = mapped_column(String(100))
    water_source: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    establishment: Mapped["Establishment"] = relationship("Establishment", back_populates="paddocks")
    animals: Mapped[list["Animal"]] = relationship(
        "Animal", back_populates="paddock", lazy="noload"
    )
    geofences: Mapped[list["Geofence"]] = relationship(
        "Geofence", back_populates="paddock", lazy="noload"
    )
