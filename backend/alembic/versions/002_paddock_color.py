"""add paddock color

Revision ID: 002
Revises: 001
Create Date: 2026-06-15 23:40:00
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paddocks", sa.Column("color", sa.String(length=20), server_default="#22c55e", nullable=True))
    op.execute("UPDATE paddocks SET color = '#22c55e' WHERE color IS NULL")


def downgrade() -> None:
    op.drop_column("paddocks", "color")
