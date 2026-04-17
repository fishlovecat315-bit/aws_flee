"""Initial tables

Revision ID: 0001
Revises: None
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- raw_cost_records ---
    op.create_table(
        "raw_cost_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.String(20), nullable=False),
        sa.Column("account_name", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("service", sa.String(100), nullable=False),
        sa.Column("tag_key", sa.String(100), nullable=True),
        sa.Column("tag_value", sa.String(200), nullable=True),
        sa.Column("amount_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column(
            "currency", sa.String(10), server_default="USD", nullable=False
        ),
        sa.Column(
            "synced_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "date",
            "service",
            "tag_key",
            "tag_value",
            name="uq_raw_cost_records",
        ),
        if_not_exists=True,
    )

    # --- allocation_rules ---
    op.create_table(
        "allocation_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_name", sa.String(50), nullable=False),
        sa.Column("tag_value", sa.String(200), nullable=True),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("business_module", sa.String(100), nullable=True),
        sa.Column("department", sa.String(50), nullable=True),
        sa.Column("ratios", JSONB(), nullable=True),
        sa.Column("special_config", JSONB(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # --- allocated_cost_records ---
    op.create_table(
        "allocated_cost_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("account_name", sa.String(50), nullable=False),
        sa.Column("tag_value", sa.String(200), nullable=True),
        sa.Column("business_module", sa.String(100), nullable=True),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("amount_usd", sa.Numeric(12, 4), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["allocation_rules.id"],
            name="fk_allocated_cost_records_rule_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_allocated_date", "allocated_cost_records", ["date"], unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "idx_allocated_dept",
        "allocated_cost_records",
        ["department"],
        unique=False,
        if_not_exists=True,
    )

    # --- allocation_rule_history ---
    op.create_table(
        "allocation_rule_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "changed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.Column("old_value", JSONB(), nullable=True),
        sa.Column("new_value", JSONB(), nullable=True),
        sa.Column(
            "changed_by",
            sa.String(100),
            server_default=sa.text("'admin'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    # --- alert_thresholds ---
    op.create_table(
        "alert_thresholds",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("monthly_threshold_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department", name="uq_alert_thresholds_department"),
        if_not_exists=True,
    )

    # --- sync_logs ---
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("accounts_synced", sa.String(200), nullable=True),
        sa.Column("records_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("sync_logs")
    op.drop_table("alert_thresholds")
    op.drop_table("allocation_rule_history")
    op.drop_index("idx_allocated_dept", table_name="allocated_cost_records")
    op.drop_index("idx_allocated_date", table_name="allocated_cost_records")
    op.drop_table("allocated_cost_records")
    op.drop_table("allocation_rules")
    op.drop_table("raw_cost_records")
