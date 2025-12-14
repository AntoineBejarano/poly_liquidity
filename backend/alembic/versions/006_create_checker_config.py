"""Create checker_config table

Revision ID: 006_create_checker_config
Revises: 005_improve_system_config
Create Date: 2025-01-13 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_create_checker_config'
down_revision = '005_improve_system_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'checker_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('checker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(50), nullable=False),  # "float", "int", "bool", "string", "json"
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('checker_id', 'key', name='uq_checker_config_checker_key'),
        sa.ForeignKeyConstraint(['checker_id'], ['event_checkers.id'], name='fk_checker_config_checker'),
    )
    
    # Create indexes
    op.create_index('ix_checker_config_checker_id', 'checker_config', ['checker_id'])
    op.create_index('ix_checker_config_key', 'checker_config', ['key'])


def downgrade() -> None:
    op.drop_index('ix_checker_config_key', table_name='checker_config')
    op.drop_index('ix_checker_config_checker_id', table_name='checker_config')
    op.drop_table('checker_config')

