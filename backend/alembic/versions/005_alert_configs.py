"""alert configs

Revision ID: 005
Revises: 004
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Track notification timestamp on alerts for repeat logic
    op.add_column("alerts", sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "alert_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("establishment_id", UUID(as_uuid=True), sa.ForeignKey("establishments.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("alert_type", sa.String(length=40), nullable=False, index=True),
        sa.Column("enabled", sa.Boolean, server_default="true", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="warning", nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("threshold_min", sa.Float(), nullable=True),
        sa.Column("threshold_max", sa.Float(), nullable=True),
        sa.Column("repeat_interval_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("browser_notify", sa.Boolean, server_default="true", nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
    )
    # Una sola configuración por tipo de alerta por tenant
    op.create_index(
        "ix_alert_configs_tenant_type",
        "alert_configs",
        ["tenant_id", "alert_type"],
        unique=True,
    )

    # Seed de configuraciones por defecto para cada tenant existente
    op.execute("""
        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'temperature_low', true, 'critical', NULL, 0.0, NULL, 240, true, 'Temperatura baja'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'temperature_low'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'temperature_high', true, 'critical', NULL, NULL, 40.0, 240, true, 'Temperatura alta'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'temperature_high'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'low_battery', true, 'warning', 20.0, NULL, NULL, 1440, true, 'Batería baja'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'low_battery'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'device_offline', true, 'warning', NULL, NULL, NULL, 0, false, 'Dispositivo offline'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'device_offline'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'prolonged_disconnect', true, 'critical', 60.0, NULL, NULL, 60, true, 'Desconexión prolongada'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'prolonged_disconnect'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'outside_geofence', true, 'warning', NULL, NULL, NULL, 0, true, 'Fuera de geocerca'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'outside_geofence'
        );

        INSERT INTO alert_configs (tenant_id, alert_type, enabled, severity, threshold_value, threshold_min, threshold_max, repeat_interval_minutes, browser_notify, name)
        SELECT t.id, 'outside_field', true, 'critical', NULL, NULL, NULL, 0, true, 'Fuera de campo'
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM alert_configs ac WHERE ac.tenant_id = t.id AND ac.alert_type = 'outside_field'
        );
    """)


def downgrade() -> None:
    op.drop_index("ix_alert_configs_tenant_type", table_name="alert_configs")
    op.drop_table("alert_configs")
    op.drop_column("alerts", "last_notified_at")
