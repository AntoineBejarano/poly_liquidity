"""Create execution_session table

Revision ID: 007_create_execution_session
Revises: 006_create_checker_config
Create Date: 2025-01-13 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_create_execution_session'
down_revision = '006_create_checker_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'execution_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_name', sa.String(255), nullable=False),
        sa.Column('execution_mode', sa.String(50), nullable=False),  # "DRY_RUN", "PAPER", "LIVE"
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('started_by', sa.String(255), nullable=True),
        sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),  # "ACTIVE", "PAUSED", "STOPPED", "ERROR"
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['started_by'], ['neon_auth.users_sync.id'], name='fk_execution_session_user'),
    )
    
    # Create indexes
    op.create_index('ix_execution_session_status', 'execution_session', ['status'])
    op.create_index('ix_execution_session_mode', 'execution_session', ['execution_mode'])
    op.create_index('ix_execution_session_started_at', 'execution_session', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_execution_session_started_at', table_name='execution_session')
    op.drop_index('ix_execution_session_mode', table_name='execution_session')
    op.drop_index('ix_execution_session_status', table_name='execution_session')
    op.drop_table('execution_session')

