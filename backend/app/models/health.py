import enum
import uuid
from datetime import date
from sqlalchemy import String, Float, Text, ForeignKey, UUID, Enum as SAEnum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class HealthEventType(str, enum.Enum):
    VACCINE = "vaccine"
    TREATMENT = "treatment"
    DISEASE = "disease"
    SURGERY = "surgery"
    CHECKUP = "checkup"
    DEWORMING = "deworming"
    VITAMIN = "vitamin"


class HealthEvent(TenantScopedMixin, Base):
    __tablename__ = "health_events"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_type: Mapped[HealthEventType] = mapped_column(SAEnum(HealthEventType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(100))
    route: Mapped[str | None] = mapped_column(String(50))
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    next_date: Mapped[date | None] = mapped_column(Date)
    vet_name: Mapped[str | None] = mapped_column(String(200))
    cost: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="health_events")
