import uuid
import enum
from sqlalchemy import String, Boolean, ForeignKey, Enum as SAEnum, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import UUIDMixin, TimestampMixin
from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    TENANT_ADMIN = "tenant_admin"
    VET = "vet"
    MANAGER = "manager"
    OPERATOR = "operator"
    READONLY = "readonly"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]), default=UserRole.OPERATOR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    tenant: Mapped["Tenant | None"] = relationship("Tenant", back_populates="users")
