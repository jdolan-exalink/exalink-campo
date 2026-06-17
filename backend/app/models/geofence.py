import enum
import uuid
from sqlalchemy import String, Text, ForeignKey, UUID, Enum as SAEnum, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import TenantScopedMixin
from app.core.database import Base


class GeofenceType(str, enum.Enum):
    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    ALERT = "alert"


class Geofence(TenantScopedMixin, Base):
    __tablename__ = "geofences"

    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paddock_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paddocks.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fence_type: Mapped[GeofenceType] = mapped_column(SAEnum(GeofenceType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    polygon: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    buffer_m: Mapped[float] = mapped_column(Float, default=50.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    establishment: Mapped["Establishment"] = relationship("Establishment")
    paddock: Mapped["Paddock | None"] = relationship("Paddock", back_populates="geofences")
