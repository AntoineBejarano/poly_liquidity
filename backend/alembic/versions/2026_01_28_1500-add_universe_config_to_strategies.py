"""add_universe_config_to_strategies

Revision ID: a1b2c3d4e5f6
Revises: 7db289dfc9ea
Create Date: 2026-01-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '7db289dfc9ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Añadir universe_config a strategies
    # Contiene: categories, markets, tags, auto_attach, deny_list
    op.add_column('strategies', sa.Column('universe_config', JSONB, nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('strategies', 'universe_config')
