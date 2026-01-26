"""create execution_plans table

Revision ID: 011_create_execution_plans
Revises: 010_create_strategies_graphs
Create Date: 2025-12-20 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '011_create_execution_plans'
down_revision = '010_create_strategies_graphs'
branch_labels = None
depends_on = None


def upgrade():
    # Execution plans
    op.create_table(
        'execution_plans',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False, index=True),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False, index=True),
        
        # Plan inmutable (JSONB)
        sa.Column('legs', JSONB, nullable=False),  # List[PlanLeg dict]
        sa.Column('ttl_ms', sa.Integer, nullable=False),  # Tiempo de vida en milisegundos
        
        # Estado del plan
        sa.Column('status', sa.String, nullable=False, index=True, server_default='PLAN_BUILT'),
        # Estados: PLAN_BUILT | ABORTED | EXECUTING | COMPLETED | FAILED
        
        # Risk config a nivel plan
        sa.Column('risk_config', JSONB, nullable=False, server_default='{}'),
        
        # Trazabilidad
        sa.Column('trace_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('decision_graph_execution_id', UUID(as_uuid=True), sa.ForeignKey("graph_executions.id"), nullable=True),
        sa.Column('execution_graph_execution_id', UUID(as_uuid=True), sa.ForeignKey("graph_executions.id"), nullable=True),
        
        # Timestamps
        # IMPORTANTE: expires_at es INMUTABLE. No se recalcula, no se actualiza, no se extiende.
        sa.Column('expires_at', sa.DateTime, nullable=True),
        
        # Estado de ejecución (para observabilidad)
        sa.Column('ready_for_execution', sa.Boolean, nullable=False, server_default='false', index=True),
        sa.Column('queued_at', sa.DateTime, nullable=True),
        
        # Timestamps de BaseModel
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Índices adicionales
    op.create_index('idx_execution_plans_strategy_status', 'execution_plans', ['strategy_id', 'status'])
    op.create_index('idx_execution_plans_event_status', 'execution_plans', ['event_id', 'status'])
    op.create_index('idx_execution_plans_ready', 'execution_plans', ['ready_for_execution', 'status'])
    op.create_index('idx_execution_plans_expires_at', 'execution_plans', ['expires_at'])


def downgrade():
    op.drop_index('idx_execution_plans_expires_at', table_name='execution_plans')
    op.drop_index('idx_execution_plans_ready', table_name='execution_plans')
    op.drop_index('idx_execution_plans_event_status', table_name='execution_plans')
    op.drop_index('idx_execution_plans_strategy_status', table_name='execution_plans')
    op.drop_table('execution_plans')

