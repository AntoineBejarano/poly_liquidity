"""create tip_intents table

Revision ID: 2026_02_18_tip_intents
Revises: 2026_02_18_strategy_proxy
Create Date: 2026-02-18

Tabla tip_intents para estrategia Telegram Tipsters → PS3838.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "2026_02_18_tip_intents"
down_revision = "2026_02_18_strategy_proxy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tip_intents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("neon_auth.users_sync.id"), nullable=True),
        sa.Column("telegram_message_id", sa.String(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed", JSONB, nullable=True),
        sa.Column("ps3838_event_id", sa.Numeric(20, 0), nullable=True),
        sa.Column("ps3838_league_id", sa.Numeric(10, 0), nullable=True),
        sa.Column("ps3838_period_number", sa.Numeric(5, 0), nullable=True),
        sa.Column("ps3838_line_id", sa.String(), nullable=True),
        sa.Column("ps3838_odds", sa.Numeric(10, 4), nullable=True),
        sa.Column("suggested_stake_usd", sa.Numeric(12, 4), nullable=True),
        sa.Column("risk_class", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("ps3838_bet_id", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_tip_intents_strategy_id", "tip_intents", ["strategy_id"], unique=False)
    op.create_index("ix_tip_intents_user_id", "tip_intents", ["user_id"], unique=False)
    op.create_index("ix_tip_intents_status", "tip_intents", ["status"], unique=False)
    op.create_index("ix_tip_intents_telegram_message_id", "tip_intents", ["telegram_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tip_intents_telegram_message_id", table_name="tip_intents")
    op.drop_index("ix_tip_intents_status", table_name="tip_intents")
    op.drop_index("ix_tip_intents_user_id", table_name="tip_intents")
    op.drop_index("ix_tip_intents_strategy_id", table_name="tip_intents")
    op.drop_table("tip_intents")
