"""add_updated_at_to_decision_trace_if_missing

Revision ID: 4dc1c3deb8eb
Revises: 8f37a5e540c2
Create Date: 2025-12-14 22:50:00.421263

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4dc1c3deb8eb'
down_revision = '8f37a5e540c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if updated_at column exists, if not add it
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('decision_trace')]
    
    if 'updated_at' not in columns:
        op.add_column(
            'decision_trace',
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
        )


def downgrade() -> None:
    # Remove updated_at column if it exists
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('decision_trace')]
    
    if 'updated_at' in columns:
        op.drop_column('decision_trace', 'updated_at')

