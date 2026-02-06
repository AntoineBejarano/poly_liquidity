"""add wallet_id to strategies

Revision ID: 2026_02_06_wallet
Revises: 2026_02_03_wallets
Create Date: 2026-02-06

Permite que cada estrategia use una wallet concreta. Si es NULL, se usa la wallet activa del usuario.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '2026_02_06_wallet'
down_revision = '2026_02_03_wallets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'strategies',
        sa.Column('wallet_id', UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_strategies_wallet_id',
        'strategies',
        'wallets',
        ['wallet_id'],
        ['id'],
    )
    op.create_index('ix_strategies_wallet_id', 'strategies', ['wallet_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_strategies_wallet_id', table_name='strategies')
    op.drop_constraint('fk_strategies_wallet_id', 'strategies', type_='foreignkey')
    op.drop_column('strategies', 'wallet_id')
