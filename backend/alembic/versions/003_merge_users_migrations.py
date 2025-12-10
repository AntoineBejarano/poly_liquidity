"""merge_users_migrations

Revision ID: 003_merge
Revises: ('002_update_users_to_metadata', '4e49609a5fdf')
Create Date: 2025-01-12 21:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_merge'
down_revision = ('002_update_users_to_metadata', '4e49609a5fdf')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration - both parent migrations have already been applied
    # No changes needed here, just merging the branches
    pass


def downgrade() -> None:
    # This is a merge migration - both parent migrations have already been applied
    # No changes needed here, just merging the branches
    pass


