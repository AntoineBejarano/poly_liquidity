"""Create decision_trace table

Revision ID: 008_create_decision_trace
Revises: 007_create_execution_session
Create Date: 2025-01-13 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_create_decision_trace'
down_revision = '007_create_execution_session'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'decision_trace',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('component', sa.String(100), nullable=False),  # "scanner", "strategy", "risk", "execution"
        sa.Column('decision_stage', sa.String(50), nullable=False),  # "SCAN", "EVENT_CONFIRMATION", "STRATEGY", "RISK", "EXECUTION"
        sa.Column('market_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decision_type', sa.String(100), nullable=False),  # "entry", "reject", "adjust", "cancel"
        sa.Column('decision', sa.String(50), nullable=False),  # "APPROVED", "REJECTED", "ADJUSTED", "CANCELLED"
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # ACOTADO: solo hashes/snapshots relevantes, NO orderbooks completos
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('config_used', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('latency_ms', sa.Float(), nullable=True),
    sa.Column('confidence_score', sa.Float(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # Renamed from 'metadata' (reserved in SQLAlchemy)
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['execution_session.id'], name='fk_decision_trace_session'),
        sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name='fk_decision_trace_market'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], name='fk_decision_trace_event'),
    )
    
    # Create indexes for performance
    op.create_index('ix_decision_trace_session', 'decision_trace', ['session_id'])
    op.create_index('ix_decision_trace_trace_id', 'decision_trace', ['trace_id'])
    op.create_index('ix_decision_trace_timestamp', 'decision_trace', ['timestamp'])
    op.create_index('ix_decision_trace_component', 'decision_trace', ['component'])
    op.create_index('ix_decision_trace_stage', 'decision_trace', ['decision_stage'])
    op.create_index('ix_decision_trace_market', 'decision_trace', ['market_id'])
    op.create_index('ix_decision_trace_decision', 'decision_trace', ['decision'])


def downgrade() -> None:
    op.drop_index('ix_decision_trace_decision', table_name='decision_trace')
    op.drop_index('ix_decision_trace_market', table_name='decision_trace')
    op.drop_index('ix_decision_trace_stage', table_name='decision_trace')
    op.drop_index('ix_decision_trace_component', table_name='decision_trace')
    op.drop_index('ix_decision_trace_timestamp', table_name='decision_trace')
    op.drop_index('ix_decision_trace_trace_id', table_name='decision_trace')
    op.drop_index('ix_decision_trace_session', table_name='decision_trace')
    op.drop_table('decision_trace')

