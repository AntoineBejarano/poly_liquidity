"""Update users table to user_metadata

Revision ID: 002_update_users_to_metadata
Revises: 001_initial
Create Date: 2025-01-12 20:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_update_users_to_metadata'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, drop the foreign key constraint from system_config that references users
    op.drop_constraint('system_config_updated_by_fkey', 'system_config', type_='foreignkey')
    
    # Drop the old users table
    op.drop_table('users')
    
    # Create user_metadata table that references neon_auth.users_sync
    op.create_table(
        'user_metadata',
        sa.Column('user_id', sa.String(), primary_key=True, nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['neon_auth.users_sync.id'], name='fk_user_metadata_user_id'),
    )
    
    # Create index on role for faster queries
    op.create_index('ix_user_metadata_role', 'user_metadata', ['role'])
    
    # Update system_config.updated_by to reference user_metadata.user_id (String instead of UUID)
    # First, we need to change the column type from UUID to String
    op.alter_column('system_config', 'updated_by',
                    type_=sa.String(),
                    existing_type=postgresql.UUID(as_uuid=True),
                    postgresql_using='updated_by::text')
    
    # Add the foreign key constraint back, now pointing to user_metadata
    op.create_foreign_key(
        'system_config_updated_by_fkey',
        'system_config', 'user_metadata',
        ['updated_by'], ['user_id']
    )


def downgrade() -> None:
    # Drop foreign key from system_config
    op.drop_constraint('system_config_updated_by_fkey', 'system_config', type_='foreignkey')
    
    # Change updated_by back to UUID
    op.alter_column('system_config', 'updated_by',
                    type_=postgresql.UUID(as_uuid=True),
                    existing_type=sa.String())
    
    # Drop user_metadata table
    op.drop_index('ix_user_metadata_role', 'user_metadata')
    op.drop_table('user_metadata')
    
    # Recreate old users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('stack_oauth_user_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Recreate foreign key constraint
    op.create_foreign_key(
        'system_config_updated_by_fkey',
        'system_config', 'users',
        ['updated_by'], ['id']
    )

