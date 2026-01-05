"""add_subscription_plans

Revision ID: a1b2c3d4e5f6
Revises: d53f042798a1
Create Date: 2025-12-31

Adds subscription_plans table with doctor limits per plan.
Adds plan_id and max_doctors_override to clinics table.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d53f042798a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subscription plans table and clinic columns."""
    # 1. Create subscription_plans table
    op.create_table(
        "subscription_plans",
        sa.Column("plan_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("max_doctors", sa.Integer(), nullable=True),  # NULL = unlimited
        sa.Column("features", sa.JSON(), nullable=True),  # Use JSON for SQLite compatibility
        sa.Column(
            "price_usd", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_subscription_plans_name", "subscription_plans", ["name"], unique=True)

    # 2. Seed default plans (using Python-generated UUIDs for SQLite compatibility)
    free_id = str(uuid.uuid4())
    pro_id = str(uuid.uuid4())
    enterprise_id = str(uuid.uuid4())

    op.execute(f"""
        INSERT INTO subscription_plans (plan_id, name, display_name, max_doctors, features, price_usd)
        VALUES
            ('{free_id}', 'free', 'Plan Gratuito', 2, '["checkin_qr"]', 0),
            ('{pro_id}', 'pro', 'Plan Profesional', 10, '["checkin_qr", "chat", "whatsapp"]', 29.99),
            ('{enterprise_id}', 'enterprise', 'Plan Empresarial', NULL, '["checkin_qr", "chat", "whatsapp", "payments", "analytics"]', 99.99)
    """)

    # 3. Add new columns to clinics (using batch mode for SQLite FK support)
    with op.batch_alter_table("clinics", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_id", sa.UUID(as_uuid=False), nullable=True))
        batch_op.add_column(sa.Column("max_doctors_override", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_clinics_subscription_plan",
            "subscription_plans",
            ["plan_id"],
            ["plan_id"],
        )

    # 4. Migrate existing clinics to free plan
    op.execute(f"""
        UPDATE clinics
        SET plan_id = '{free_id}'
        WHERE plan_id IS NULL
    """)


def downgrade() -> None:
    """Remove subscription plans table and clinic columns."""
    # 1. Remove foreign key and columns from clinics (using batch mode for SQLite)
    with op.batch_alter_table("clinics", schema=None) as batch_op:
        batch_op.drop_constraint("fk_clinics_subscription_plan", type_="foreignkey")
        batch_op.drop_column("max_doctors_override")
        batch_op.drop_column("plan_id")

    # 2. Drop index and table
    op.drop_index("ix_subscription_plans_name", table_name="subscription_plans")
    op.drop_table("subscription_plans")
