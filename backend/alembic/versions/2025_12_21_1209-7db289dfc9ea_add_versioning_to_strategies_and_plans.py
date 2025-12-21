"""add_versioning_to_strategies_and_plans

Revision ID: 7db289dfc9ea
Revises: 5db3d648921b
Create Date: 2025-12-21 12:09:59.654480

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7db289dfc9ea'
down_revision = '5db3d648921b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects.postgresql import JSONB
    # Añadir pinned_node_versions a strategies
    op.add_column('strategies', sa.Column('pinned_node_versions', JSONB, nullable=True))
    # Añadir node_versions a execution_plans
    op.add_column('execution_plans', sa.Column('node_versions', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('execution_plans', 'node_versions')
    op.drop_column('strategies', 'pinned_node_versions')

