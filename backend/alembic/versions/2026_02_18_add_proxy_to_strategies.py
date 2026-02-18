"""add proxy_id and connection_proxies to strategies

Revision ID: 2026_02_18_strategy_proxy
Revises: 2026_02_18_proxies
Create Date: 2026-02-18

proxy_id: proxy global para toda la estrategia.
connection_proxies: JSONB NOT NULL default {} - mapa connection_key -> proxy_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = '2026_02_18_strategy_proxy'
down_revision = '2026_02_18_proxies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'strategies',
        sa.Column('proxy_id', UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        'strategies',
        sa.Column('connection_proxies', JSONB, nullable=False, server_default='{}'),
    )
    op.create_foreign_key(
        'fk_strategies_proxy_id',
        'strategies',
        'proxies',
        ['proxy_id'],
        ['id'],
    )
    op.create_index('ix_strategies_proxy_id', 'strategies', ['proxy_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_strategies_proxy_id', table_name='strategies')
    op.drop_constraint('fk_strategies_proxy_id', 'strategies', type_='foreignkey')
    op.drop_column('strategies', 'connection_proxies')
    op.drop_column('strategies', 'proxy_id')
