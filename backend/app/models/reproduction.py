import enum
import uuid
from datetime import date
from sqlalchemy import String, Text, ForeignKey, UUID, Enum as SAEnum, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class ReproductionEventType(str, enum.Enum):
    HEAT = "heat"
    SERVICE = "service"
    INSEMINATION = "insemination"
    PREGNANCY_CHECK = "pregnancy_check"
    BIRTH = "birth"
    ABORTION = "abortion"
    DRYING = "drying"


class ReproductionEvent(TenantScopedMixin, Base):
    __tablename__ = "reproduction_events"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bull_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="SET NULL"), nullable=True
    )

    event_type: Mapped[ReproductionEventType] = mapped_column(SAEnum(ReproductionEventType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    expected_birth_date: Mapped[date | None] = mapped_column(Date)
    is_pregnant: Mapped[bool | None] = mapped_column(Boolean)
    result: Mapped[str | None] = mapped_column(String(200))
    semen_batch: Mapped[str | None] = mapped_column(String(100))
    vet_name: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    animal: Mapped["Animal"] = relationship(
        "Animal", back_populates="reproduction_events", foreign_keys=[animal_id]
    )
