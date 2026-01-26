"""Improve system_config table

Revision ID: 005_improve_system_config
Revises: 004_add_condition_clob_tokens
Create Date: 2025-01-13 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_improve_system_config'
down_revision = '004_add_condition_clob_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('system_config')]
    indexes = [idx['name'] for idx in inspector.get_indexes('system_config')]
    
    # Add execution_mode column
    if 'execution_mode' not in columns:
        op.add_column('system_config', sa.Column('execution_mode', sa.String(50), nullable=True))
    
    # Add min_value and max_value for validation
    if 'min_value' not in columns:
        op.add_column('system_config', sa.Column('min_value', sa.String(), nullable=True))
    if 'max_value' not in columns:
        op.add_column('system_config', sa.Column('max_value', sa.String(), nullable=True))
    
    # Add is_readonly flag (protección para parámetros críticos)
    if 'is_readonly' not in columns:
        op.add_column('system_config', sa.Column('is_readonly', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add requires_confirmation flag (requiere confirmación antes de cambiar)
    if 'requires_confirmation' not in columns:
        op.add_column('system_config', sa.Column('requires_confirmation', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add validation_rule JSONB
    if 'validation_rule' not in columns:
        op.add_column('system_config', sa.Column('validation_rule', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Add updated_at timestamp
    if 'updated_at' not in columns:
        op.add_column('system_config', sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))
    
    # Create index on category for faster queries
    if 'ix_system_config_category' not in indexes:
        op.create_index('ix_system_config_category', 'system_config', ['category'])
    
    # Create index on execution_mode
    if 'ix_system_config_execution_mode' not in indexes:
        op.create_index('ix_system_config_execution_mode', 'system_config', ['execution_mode'])
    
    # Create index on is_readonly for queries de parámetros protegidos
    if 'ix_system_config_is_readonly' not in indexes:
        op.create_index('ix_system_config_is_readonly', 'system_config', ['is_readonly'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_system_config_is_readonly', table_name='system_config')
    op.drop_index('ix_system_config_execution_mode', table_name='system_config')
    op.drop_index('ix_system_config_category', table_name='system_config')
    
    # Drop columns
    op.drop_column('system_config', 'updated_at')
    op.drop_column('system_config', 'validation_rule')
    op.drop_column('system_config', 'requires_confirmation')
    op.drop_column('system_config', 'is_readonly')
    op.drop_column('system_config', 'max_value')
    op.drop_column('system_config', 'min_value')
    op.drop_column('system_config', 'execution_mode')

