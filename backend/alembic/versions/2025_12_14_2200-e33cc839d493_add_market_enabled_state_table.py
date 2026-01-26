"""add_market_enabled_state_table

Revision ID: e33cc839d493
Revises: 009_add_series_markets_events
Create Date: 2025-12-14 22:00:50.256964

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e33cc839d493'
down_revision = '009_add_series_markets_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla market_enabled_states
    op.create_table(
        'market_enabled_states',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('polymarket_market_id', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('polymarket_market_id', name='uq_market_enabled_state')
    )
    op.create_index(op.f('ix_market_enabled_states_polymarket_market_id'), 'market_enabled_states', ['polymarket_market_id'], unique=True)
    op.create_index(op.f('ix_market_enabled_states_enabled'), 'market_enabled_states', ['enabled'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_market_enabled_states_enabled'), table_name='market_enabled_states')
    op.drop_index(op.f('ix_market_enabled_states_polymarket_market_id'), table_name='market_enabled_states')
    op.drop_table('market_enabled_states')

