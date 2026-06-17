"""fields zones and movement log

Revision ID: 003
Revises: 002
Create Date: 2026-06-16 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("establishments", sa.Column("color", sa.String(length=20), server_default="#3b82f6", nullable=True))
    op.execute("UPDATE establishments SET color = '#3b82f6' WHERE color IS NULL")
    op.create_table(
        "device_zone_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dev_addr", sa.String(length=100), nullable=False),
        sa.Column("field_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("field_name", sa.String(length=200), nullable=True),
        sa.Column("paddock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paddock_name", sa.String(length=100), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_device_zone_events_dev_created", "device_zone_events", ["dev_addr", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_device_zone_events_dev_created", table_name="device_zone_events")
    op.drop_table("device_zone_events")
    op.drop_column("establishments", "color")
