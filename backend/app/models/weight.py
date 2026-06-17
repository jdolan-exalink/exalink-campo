import uuid
from datetime import date
from sqlalchemy import String, Float, Text, ForeignKey, UUID, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class WeightRecord(TenantScopedMixin, Base):
    __tablename__ = "weight_records"

    animal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("animals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    measure_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    method: Mapped[str | None] = mapped_column(String(50))
    device_uid: Mapped[str | None] = mapped_column(String(100))
    daily_gain: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="weights")
