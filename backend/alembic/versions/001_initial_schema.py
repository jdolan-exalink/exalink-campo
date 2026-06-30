"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # tenants
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(50), server_default="basic"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("max_animals", sa.Integer, server_default="1000"),
        sa.Column("max_devices", sa.Integer, server_default="50"),
        sa.Column("settings", sa.JSON, server_default="{}"),
        sa.Column("contact_email", sa.String(200)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("logo_url", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), server_default="operator"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("phone", sa.String(50)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # establishments
    op.create_table(
        "establishments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50)),
        sa.Column("color", sa.String(20), server_default="#3b82f6"),
        sa.Column("address", sa.Text),
        sa.Column("province", sa.String(100)),
        sa.Column("municipality", sa.String(100)),
        sa.Column("total_area_ha", sa.Float),
        sa.Column("renspa", sa.String(100)),
        sa.Column("senasa_code", sa.String(100)),
        sa.Column("location", Geometry("POINT", srid=4326)),
        sa.Column("boundary", Geometry("POLYGON", srid=4326)),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )
    op.create_index("ix_establishments_tenant_id", "establishments", ["tenant_id"])

    # herds
    op.create_table(
        "herds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paddock_id", UUID(as_uuid=True)),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("breed", sa.String(100)),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )

    # paddocks
    op.create_table(
        "paddocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("area_ha", sa.Float),
        sa.Column("max_capacity", sa.Integer),
        sa.Column("current_load", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(50), server_default="empty"),
        sa.Column("polygon", Geometry("POLYGON", srid=4326)),
        sa.Column("pasture_type", sa.String(100)),
        sa.Column("water_source", sa.Boolean, server_default="true"),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )
    op.create_index("ix_paddocks_tenant_id", "paddocks", ["tenant_id"])
    op.create_index("ix_paddocks_establishment_id", "paddocks", ["establishment_id"])

    # animals
    op.create_table(
        "animals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paddock_id", UUID(as_uuid=True), sa.ForeignKey("paddocks.id", ondelete="SET NULL")),
        sa.Column("herd_id", UUID(as_uuid=True), sa.ForeignKey("herds.id", ondelete="SET NULL")),
        sa.Column("ear_tag", sa.String(50), nullable=False),
        sa.Column("rfid", sa.String(100), unique=True),
        sa.Column("name", sa.String(100)),
        sa.Column("breed", sa.String(100)),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("category", sa.String(20)),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("birth_date", sa.Date),
        sa.Column("color", sa.String(50)),
        sa.Column("weight_kg", sa.Float),
        sa.Column("mother_id", UUID(as_uuid=True)),
        sa.Column("father_id", UUID(as_uuid=True)),
        sa.Column("purchase_date", sa.Date),
        sa.Column("purchase_price", sa.Float),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )
    op.create_index("ix_animals_tenant_id", "animals", ["tenant_id"])
    op.create_index("ix_animals_establishment_id", "animals", ["establishment_id"])
    op.create_index("ix_animals_ear_tag", "animals", ["ear_tag"])

    # devices
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="SET NULL")),
        sa.Column("device_uid", sa.String(100), unique=True, nullable=False),
        sa.Column("device_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100)),
        sa.Column("firmware", sa.String(50)),
        sa.Column("sim_iccid", sa.String(50)),
        sa.Column("imei", sa.String(50)),
        sa.Column("battery_pct", sa.Integer),
        sa.Column("rssi", sa.Integer),
        sa.Column("temperature", sa.Float),
        sa.Column("activity_score", sa.Integer),
        sa.Column("is_online", sa.Boolean, server_default="false"),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("last_location", Geometry("POINT", srid=4326)),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )
    op.create_index("ix_devices_tenant_id", "devices", ["tenant_id"])
    op.create_index("ix_devices_device_uid", "devices", ["device_uid"])

    # locations
    op.create_table(
        "locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="SET NULL")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("point", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("battery_pct", sa.Integer),
        sa.Column("rssi", sa.Integer),
        sa.Column("temperature", sa.Float),
        sa.Column("activity_score", sa.Integer),
        sa.Column("speed_kmh", sa.Float),
        sa.Column("altitude_m", sa.Float),
    )
    op.create_index("ix_locations_device_timestamp", "locations", ["device_id", "timestamp"])
    op.create_index("ix_locations_animal_timestamp", "locations", ["animal_id", "timestamp"])

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE")),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="SET NULL")),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="SET NULL")),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", UUID(as_uuid=True)),
        sa.Column("notified", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )
    op.create_index("ix_alerts_tenant_id", "alerts", ["tenant_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    # health_events
    op.create_table(
        "health_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("dose", sa.String(100)),
        sa.Column("route", sa.String(50)),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("next_date", sa.Date),
        sa.Column("vet_name", sa.String(200)),
        sa.Column("cost", sa.Float),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )

    # reproduction_events
    op.create_table(
        "reproduction_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bull_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("expected_birth_date", sa.Date),
        sa.Column("is_pregnant", sa.Boolean),
        sa.Column("result", sa.String(200)),
        sa.Column("semen_batch", sa.String(100)),
        sa.Column("vet_name", sa.String(200)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )

    # weight_records
    op.create_table(
        "weight_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("animal_id", UUID(as_uuid=True), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_kg", sa.Float, nullable=False),
        sa.Column("measure_date", sa.Date, nullable=False),
        sa.Column("method", sa.String(50)),
        sa.Column("device_uid", sa.String(100)),
        sa.Column("daily_gain", sa.Float),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )

    # geofences
    op.create_table(
        "geofences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paddock_id", UUID(as_uuid=True), sa.ForeignKey("paddocks.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("fence_type", sa.String(20), nullable=False),
        sa.Column("polygon", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("buffer_m", sa.Float, server_default="50.0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
    )


def downgrade() -> None:
    op.drop_table("geofences")
    op.drop_table("weight_records")
    op.drop_table("reproduction_events")
    op.drop_table("health_events")
    op.drop_table("alerts")
    op.drop_table("locations")
    op.drop_table("devices")
    op.drop_table("animals")
    op.drop_table("paddocks")
    op.drop_table("herds")
    op.drop_table("establishments")
    op.drop_table("users")
    op.drop_table("tenants")
