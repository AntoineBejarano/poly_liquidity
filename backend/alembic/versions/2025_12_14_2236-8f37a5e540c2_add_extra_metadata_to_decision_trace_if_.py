"""add_extra_metadata_to_decision_trace_if_missing

Revision ID: 8f37a5e540c2
Revises: e33cc839d493
Create Date: 2025-12-14 22:36:55.465132

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f37a5e540c2'
down_revision = 'e33cc839d493'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if extra_metadata column exists, if not add it
    from sqlalchemy import inspect, text
    from sqlalchemy.dialects import postgresql
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('decision_trace')]
    
    if 'extra_metadata' not in columns:
        op.add_column(
            'decision_trace',
            sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        )


def downgrade() -> None:
    # Remove extra_metadata column if it exists
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('decision_trace')]
    
    if 'extra_metadata' in columns:
        op.drop_column('decision_trace', 'extra_metadata')

