import uuid
from sqlalchemy import String, Text, ForeignKey, UUID, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base


class Herd(TenantScopedMixin, Base):
    __tablename__ = "herds"

    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paddock_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("paddocks.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    breed: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    establishment: Mapped["Establishment"] = relationship("Establishment", back_populates="herds")
    animals: Mapped[list["Animal"]] = relationship("Animal", back_populates="herd", lazy="noload")
