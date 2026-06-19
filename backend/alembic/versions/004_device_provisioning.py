"""device provisioning

Revision ID: 004
Revises: 003
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Devices can exist in inventory (no tenant) before being claimed
    op.alter_column("devices", "tenant_id", nullable=True)
    op.alter_column("devices", "establishment_id", nullable=True)

    op.add_column("devices", sa.Column("provision_code", sa.String(9), nullable=True))
    op.add_column("devices", sa.Column("is_provisioned", sa.Boolean, server_default="false", nullable=False))
    op.add_column("devices", sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("provisioned_by", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_devices_provision_code", "devices", ["provision_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_devices_provision_code", "devices")
    op.drop_column("devices", "provisioned_by")
    op.drop_column("devices", "provisioned_at")
    op.drop_column("devices", "is_provisioned")
    op.drop_column("devices", "provision_code")
    op.alter_column("devices", "establishment_id", nullable=False)
    op.alter_column("devices", "tenant_id", nullable=False)
