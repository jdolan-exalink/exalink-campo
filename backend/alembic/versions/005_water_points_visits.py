"""water points and zone visits (traceability)

Revision ID: 005
Revises: 004
Create Date: 2026-06-18 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "water_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="water"),
        sa.Column("location", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("radius_m", sa.Float(), nullable=False, server_default="30"),
        sa.Column("capacity_l", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_water_points_establishment", "water_points", ["establishment_id"])

    op.create_table(
        "zone_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dev_addr", sa.String(100), nullable=False),
        sa.Column("animal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("establishment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paddock_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paddock_name", sa.String(100), nullable=True),
        sa.Column("water_point_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("water_point_name", sa.String(100), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_zone_visits_dev_ts", "zone_visits", ["dev_addr", "entered_at"])
    op.create_index("ix_zone_visits_animal_ts", "zone_visits", ["animal_id", "entered_at"])
    op.create_index("ix_zone_visits_day", "zone_visits", ["dev_addr", "day"])


def downgrade() -> None:
    op.drop_index("ix_zone_visits_day", table_name="zone_visits")
    op.drop_index("ix_zone_visits_animal_ts", table_name="zone_visits")
    op.drop_index("ix_zone_visits_dev_ts", table_name="zone_visits")
    op.drop_table("zone_visits")
    op.drop_index("ix_water_points_establishment", table_name="water_points")
    op.drop_table("water_points")
