"""alert configs

Revision ID: 006
Revises: 005
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
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
    seeds = [
        ("temperature_low",      True,  "critical", None,    0.0,   None,  240, True,  "Temperatura baja"),
        ("temperature_high",     True,  "critical", None,    None,  40.0,  240, True,  "Temperatura alta"),
        ("low_battery",          True,  "warning",  20.0,   None,  None,  1440, True, "Batería baja"),
        ("device_offline",       True,  "warning",  None,   None,  None,  0,    False, "Dispositivo offline"),
        ("prolonged_disconnect", True,  "critical", 60.0,   None,  None,  60,   True,  "Desconexión prolongada"),
        ("outside_geofence",     True,  "warning",  None,   None,  None,  0,    True,  "Fuera de geocerca"),
        ("outside_field",        True,  "critical", None,   None,  None,  0,    True,  "Fuera de campo"),
    ]
    for alert_type, enabled, severity, tval, tmin, tmax, repeat, browser_notify, name in seeds:
        enabled_lit = "true" if enabled else "false"
        browser_lit = "true" if browser_notify else "false"
        op.execute(
            f"""
            INSERT INTO alert_configs
                (tenant_id, alert_type, enabled, severity,
                 threshold_value, threshold_min, threshold_max,
                 repeat_interval_minutes, browser_notify, name)
            SELECT t.id, '{alert_type}', {enabled_lit}, '{severity}',
                   {tval if tval is not None else 'NULL'},
                   {tmin if tmin is not None else 'NULL'},
                   {tmax if tmax is not None else 'NULL'},
                   {repeat}, {browser_lit}, '{name.replace("'", "''")}'
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM alert_configs ac
                WHERE ac.tenant_id = t.id AND ac.alert_type = '{alert_type}'
            )
            """
        )


def downgrade() -> None:
    op.drop_index("ix_alert_configs_tenant_type", table_name="alert_configs")
    op.drop_table("alert_configs")
    op.drop_column("alerts", "last_notified_at")
