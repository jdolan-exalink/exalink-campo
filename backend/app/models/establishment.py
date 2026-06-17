from sqlalchemy import String, Float, Text, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.models.base import TenantScopedMixin
from app.core.database import Base


class Establishment(TenantScopedMixin, Base):
    __tablename__ = "establishments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), index=True)
    color: Mapped[str | None] = mapped_column(String(20), default="#3b82f6")
    address: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(100))
    municipality: Mapped[str | None] = mapped_column(String(100))
    total_area_ha: Mapped[float | None] = mapped_column(Float)
    renspa: Mapped[str | None] = mapped_column(String(100))
    senasa_code: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[object | None] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    boundary: Mapped[object | None] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="establishments")
    paddocks: Mapped[list["Paddock"]] = relationship(
        "Paddock", back_populates="establishment", lazy="noload"
    )
    animals: Mapped[list["Animal"]] = relationship(
        "Animal", back_populates="establishment", lazy="noload"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="establishment", lazy="noload"
    )
    herds: Mapped[list["Herd"]] = relationship(
        "Herd", back_populates="establishment", lazy="noload"
    )
