import uuid
from sqlalchemy import String, Text, ForeignKey, UUID, Enum as SAEnum, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TenantScopedMixin
from app.core.database import Base
from app.models.alert import AlertType, AlertSeverity


class AlertConfig(TenantScopedMixin, Base):
    """Configuración de una regla de alerta por tenant.

    threshold_value  -> umbral simple (batería %, minutos de desconexión)
    threshold_min    -> límite inferior (ej. temperatura baja)
    threshold_max    -> límite superior (ej. temperatura alta)
    repeat_interval_minutes -> cada cuánto re-notificar si la condición persiste (0 = sin repetición)
    browser_notify   -> si emite notificación del navegador
    """
    __tablename__ = "alert_configs"

    establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("establishments.id", ondelete="CASCADE"), nullable=True, index=True
    )

    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=AlertSeverity.WARNING,
    )

    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    repeat_interval_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    browser_notify: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="alert_configs")
