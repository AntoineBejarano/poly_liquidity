"""
Create equity_snapshots table.

Revision ID: 013_create_equity_snapshots
Revises: 012_add_triggers_execution_graph
Create Date: 2025-12-21 23:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '013_create_equity_snapshots'
down_revision = '012_add_triggers_execution_graph'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'equity_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('snapshot_time', sa.DateTime(), nullable=False),
        sa.Column('equity', sa.Float(), nullable=False),
        sa.Column('base_equity', sa.Float(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unrealized_pnl', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('global_exposure', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create index on snapshot_time for efficient time range queries
    op.create_index('idx_equity_snapshot_time', 'equity_snapshots', ['snapshot_time'])


def downgrade():
    op.drop_index('idx_equity_snapshot_time', table_name='equity_snapshots')
    op.drop_table('equity_snapshots')

