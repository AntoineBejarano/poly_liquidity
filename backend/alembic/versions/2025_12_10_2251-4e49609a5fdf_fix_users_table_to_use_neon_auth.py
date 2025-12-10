"""fix_users_table_to_use_neon_auth

Revision ID: 4e49609a5fdf
Revises: 001_initial
Create Date: 2025-12-10 22:51:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4e49609a5fdf'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old users table if it exists
    op.drop_table('users', if_exists=True)
    
    # Create user_metadata table
    # Note: The actual user data comes from neon_auth.users_sync (managed by Stack Auth)
    op.create_table(
        'user_metadata',
        sa.Column('user_id', sa.String(), primary_key=True, nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Add foreign key constraint to neon_auth.users_sync
    op.create_foreign_key(
        'fk_user_metadata_user_id',
        'user_metadata',
        'neon_auth.users_sync',
        ['user_id'],
        ['id']
    )
    
    # Update system_config.updated_by to reference neon_auth.users_sync.id (String) instead of users.id (UUID)
    # First, drop the old foreign key constraint
    op.drop_constraint('system_config_updated_by_fkey', 'system_config', type_='foreignkey', if_exists=True)
    
    # Change the column type from UUID to String
    op.alter_column('system_config', 'updated_by',
                    existing_type=postgresql.UUID(as_uuid=True),
                    type_=sa.String(),
                    existing_nullable=True)
    
    # Add new foreign key constraint to neon_auth.users_sync
    op.create_foreign_key(
        'fk_system_config_updated_by',
        'system_config',
        'neon_auth.users_sync',
        ['updated_by'],
        ['id']
    )


def downgrade() -> None:
    # Revert system_config.updated_by back to UUID
    op.drop_constraint('fk_system_config_updated_by', 'system_config', type_='foreignkey')
    op.alter_column('system_config', 'updated_by',
                    existing_type=sa.String(),
                    type_=postgresql.UUID(as_uuid=True),
                    existing_nullable=True)
    op.create_foreign_key('system_config_updated_by_fkey', 'system_config', 'users', ['updated_by'], ['id'])
    
    # Drop user_metadata table
    op.drop_table('user_metadata')
    
    # Recreate users table (simplified version)
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('stack_oauth_user_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
