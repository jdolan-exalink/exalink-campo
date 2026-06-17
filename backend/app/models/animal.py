import enum
import uuid
from datetime import date, datetime
from sqlalchemy import String, Float, Text, ForeignKey, UUID, Enum as SAEnum, Date, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class AnimalSex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class AnimalStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    DEAD = "dead"
    SICK = "sick"
    QUARANTINE = "quarantine"
    TRANSFERRED = "transferred"


class AnimalCategory(str, enum.Enum):
    TERNERO = "ternero"
    TERNERA = "ternera"
    NOVILLO = "novillo"
    VAQUILLONA = "vaquillona"
    TORO = "toro"
    VACA = "vaca"
    BUEY = "buey"


class Animal(TenantScopedMixin, Base):
    __tablename__ = "animals"

    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paddock_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paddocks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    herd_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("herds.id", ondelete="SET NULL"), nullable=True, index=True
    )

    ear_tag: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rfid: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    breed: Mapped[str | None] = mapped_column(String(100))
    sex: Mapped[AnimalSex] = mapped_column(SAEnum(AnimalSex, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    category: Mapped[AnimalCategory | None] = mapped_column(SAEnum(AnimalCategory, native_enum=False, values_callable=lambda x: [e.value for e in x]))
    status: Mapped[AnimalStatus] = mapped_column(SAEnum(AnimalStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=AnimalStatus.ACTIVE)
    birth_date: Mapped[date | None] = mapped_column(Date)
    color: Mapped[str | None] = mapped_column(String(50))
    weight_kg: Mapped[float | None] = mapped_column(Float)
    mother_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("animals.id"), nullable=True)
    father_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("animals.id"), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="animals")
    establishment: Mapped["Establishment"] = relationship("Establishment", back_populates="animals")
    paddock: Mapped["Paddock | None"] = relationship("Paddock", back_populates="animals")
    herd: Mapped["Herd | None"] = relationship("Herd", back_populates="animals")
    device: Mapped["Device | None"] = relationship(
        "Device", back_populates="animal", uselist=False, lazy="noload"
    )
    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="animal", lazy="noload", order_by="Location.timestamp.desc()"
    )
    health_events: Mapped[list["HealthEvent"]] = relationship(
        "HealthEvent", back_populates="animal", lazy="noload"
    )
    reproduction_events: Mapped[list["ReproductionEvent"]] = relationship(
        "ReproductionEvent",
        back_populates="animal",
        lazy="noload",
        foreign_keys="[ReproductionEvent.animal_id]",
    )
    weights: Mapped[list["WeightRecord"]] = relationship(
        "WeightRecord", back_populates="animal", lazy="noload"
    )
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="animal", lazy="noload")
