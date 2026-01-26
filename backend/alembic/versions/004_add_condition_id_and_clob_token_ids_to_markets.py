"""Add condition_id and clob_token_ids to markets

Revision ID: 004_add_condition_clob_tokens
Revises: 003_merge
Create Date: 2025-01-13 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_condition_clob_tokens'
down_revision = '003_merge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add condition_id column to markets table
    op.add_column('markets', sa.Column('condition_id', sa.String(), nullable=True))
    op.create_index('ix_markets_condition_id', 'markets', ['condition_id'])
    
    # Add clob_token_ids column to markets table (JSON)
    op.add_column('markets', sa.Column('clob_token_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove index and column
    op.drop_index('ix_markets_condition_id', table_name='markets')
    op.drop_column('markets', 'condition_id')
    op.drop_column('markets', 'clob_token_ids')

