"""add_observability_config_to_strategies

Revision ID: 5db3d648921b
Revises: 012_add_triggers_execution_graph
Create Date: 2025-12-21 12:06:26.026494

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '5db3d648921b'
down_revision = '012_add_triggers_execution_graph'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('strategies', sa.Column('observability_config', JSONB, nullable=False, server_default='{}'))


def downgrade() -> None:
    op.drop_column('strategies', 'observability_config')

