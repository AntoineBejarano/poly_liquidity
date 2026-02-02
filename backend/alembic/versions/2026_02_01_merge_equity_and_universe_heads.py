"""Merge equity_snapshots and universe_config heads.

Revision ID: b2c3d4e5f6a7
Revises: 013_create_equity_snapshots, a1b2c3d4e5f6
Create Date: 2026-02-01

Unifica las dos cabezas de la historia de migraciones:
- 013_create_equity_snapshots (tabla equity_snapshots)
- a1b2c3d4e5f6 (universe_config en strategies)
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = ('013_create_equity_snapshots', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
