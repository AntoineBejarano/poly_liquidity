"""
Add triggers and execution_graph to strategies table.

Revision ID: 012_add_triggers_execution_graph
Revises: 011_create_execution_plans
Create Date: 2025-12-21 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '012_add_triggers_execution_graph'
down_revision = '011_create_execution_plans'
branch_labels = None
depends_on = None


def upgrade():
    # Añadir columna triggers
    op.add_column(
        'strategies',
        sa.Column('triggers', JSONB, nullable=False, server_default='[]')
    )
    
    # Añadir columna execution_graph
    op.add_column(
        'strategies',
        sa.Column('execution_graph', JSONB, nullable=True)
    )


def downgrade():
    op.drop_column('strategies', 'execution_graph')
    op.drop_column('strategies', 'triggers')

