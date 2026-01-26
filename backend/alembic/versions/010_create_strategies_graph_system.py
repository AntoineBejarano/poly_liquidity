"""create strategies graph system

Revision ID: 010_create_strategies_graphs
Revises: 4dc1c3deb8eb
Create Date: 2025-12-16 23:28:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '010_create_strategies_graphs'
down_revision = '4dc1c3deb8eb'
branch_labels = None
depends_on = None


def upgrade():
    # Graph node definitions
    op.create_table(
        'graph_node_definitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('node_type', sa.String, nullable=False, unique=True, index=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String, nullable=False, index=True),
        sa.Column('path_type', sa.String, nullable=False),  # "hot" o "cold"
        sa.Column('config_schema', JSONB, nullable=False),
        sa.Column('is_builtin', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('version', sa.String, nullable=True),
        sa.Column('icon', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Strategies
    op.create_table(
        'strategies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='false', index=True),
        sa.Column('enabled_at', sa.DateTime, nullable=True),
        sa.Column('disabled_at', sa.DateTime, nullable=True),
        sa.Column('decision_graph', JSONB, nullable=False),
        sa.Column('support_graphs', JSONB, nullable=False, server_default='[]'),
        sa.Column('control_loop_config', JSONB, nullable=False, server_default='{}'),
        sa.Column('risk_config', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_by', sa.String, sa.ForeignKey("neon_auth.users_sync.id"), nullable=True),
        sa.Column('tags', JSONB, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # State cache
    op.create_table(
        'state_cache',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('cache_key', sa.String, nullable=False, unique=True, index=True),
        sa.Column('cache_value', JSONB, nullable=False),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=True, index=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=True, index=True),
        sa.Column('expires_at', sa.DateTime, nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now(), index=True),
    )
    
    # Graph executions
    op.create_table(
        'graph_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('graph_type', sa.String, nullable=False, index=True),
        sa.Column('graph_name', sa.String, nullable=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=True, index=True),
        sa.Column('status', sa.String, nullable=False, index=True),
        sa.Column('started_at', sa.DateTime, nullable=False, index=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('trace_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('node_executions', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Strategy events
    op.create_table(
        'strategy_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column('observation_started_at', sa.DateTime, nullable=True),
        sa.Column('observation_ended_at', sa.DateTime, nullable=True),
        sa.Column('event_config', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('strategy_id', 'event_id', name='uq_strategy_event'),
    )
    
    # Execution intents
    op.create_table(
        'execution_intents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False, index=True),
        sa.Column('side', sa.String, nullable=False),
        sa.Column('outcome', sa.String, nullable=False),
        sa.Column('target_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('size', sa.Numeric(18, 8), nullable=False),
        sa.Column('size_usdc', sa.Numeric(18, 8), nullable=False),
        sa.Column('reason', sa.String, nullable=False),
        sa.Column('context', JSONB, nullable=True),
        sa.Column('status', sa.String, nullable=False, server_default='PENDING', index=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.String, nullable=True),
        sa.Column('trace_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('decision_trace_id', UUID(as_uuid=True), sa.ForeignKey("decision_trace.id"), nullable=True),
        sa.Column('graph_execution_id', UUID(as_uuid=True), sa.ForeignKey("graph_executions.id"), nullable=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Strategy metrics
    op.create_table(
        'strategy_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime, nullable=False, index=True),
        sa.Column('period_end', sa.DateTime, nullable=False, index=True),
        sa.Column('total_intents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('approved_intents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('executed_intents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('rejected_intents', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_volume_usdc', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('total_pnl_usdc', sa.Numeric(18, 8), nullable=True),
        sa.Column('total_exposure_usdc', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('avg_entry_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('avg_exit_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('calculated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # External data sources
    op.create_table(
        'external_data_sources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('connector_type', sa.String, nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('connector_config', JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true', index=True),
        sa.Column('last_health_check', sa.DateTime, nullable=True),
        sa.Column('health_status', sa.String, nullable=True),
        sa.Column('created_by', sa.String, sa.ForeignKey("neon_auth.users_sync.id"), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Índices adicionales
    op.create_index('idx_strategies_active', 'strategies', ['is_active'])
    op.create_index('idx_graph_executions_strategy_event', 'graph_executions', ['strategy_id', 'event_id'])
    op.create_index('idx_state_cache_strategy_event', 'state_cache', ['strategy_id', 'event_id'])
    op.create_index('idx_execution_intents_strategy_status', 'execution_intents', ['strategy_id', 'status'])


def downgrade():
    op.drop_index('idx_execution_intents_strategy_status', table_name='execution_intents')
    op.drop_index('idx_state_cache_strategy_event', table_name='state_cache')
    op.drop_index('idx_graph_executions_strategy_event', table_name='graph_executions')
    op.drop_index('idx_strategies_active', table_name='strategies')
    op.drop_table('external_data_sources')
    op.drop_table('strategy_metrics')
    op.drop_table('execution_intents')
    op.drop_table('strategy_events')
    op.drop_table('graph_executions')
    op.drop_table('state_cache')
    op.drop_table('strategies')
    op.drop_table('graph_node_definitions')

