"""add index tip_intents for per_channel_limits query

Revision ID: 2026_02_18_tip_intent_idx
Revises: 2026_02_18_tip_intents
Create Date: 2026-02-18

Índice compuesto para la query de per_channel_limits:
strategy_id + telegram_chat_id + created_at
"""
from alembic import op

revision = "2026_02_18_tip_intent_idx"
down_revision = "2026_02_18_tip_intents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tip_intents_strategy_chat_created",
        "tip_intents",
        ["strategy_id", "telegram_chat_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tip_intents_strategy_chat_created", table_name="tip_intents")
