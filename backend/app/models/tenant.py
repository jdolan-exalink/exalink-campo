import uuid
from sqlalchemy import String, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDMixin, TimestampMixin
from app.core.database import Base


class Tenant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="basic")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_animals: Mapped[int] = mapped_column(default=1000)
    max_devices: Mapped[int] = mapped_column(default=50)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    contact_email: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="noload")
    establishments: Mapped[list["Establishment"]] = relationship(
        "Establishment", back_populates="tenant", lazy="noload"
    )
    animals: Mapped[list["Animal"]] = relationship("Animal", back_populates="tenant", lazy="noload")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="tenant", lazy="noload")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="tenant", lazy="noload")
    alert_configs: Mapped[list["AlertConfig"]] = relationship("AlertConfig", back_populates="tenant", lazy="noload")
