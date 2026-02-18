"""create proxies table

Revision ID: 2026_02_18_proxies
Revises: 2026_02_06_wallet
Create Date: 2026-02-18

Tabla proxies por usuario. Multi-tenant vía created_by.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = '2026_02_18_proxies'
down_revision = '2026_02_06_wallet'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'proxies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('proxy_type', sa.String(), nullable=False, server_default='SOCKS5'),
        sa.Column('proxy_host', sa.String(), nullable=False),
        sa.Column('proxy_port', sa.Integer(), nullable=False),
        sa.Column('proxy_username', sa.String(), nullable=True),
        sa.Column('encrypted_proxy_password', sa.LargeBinary(), nullable=True),
        sa.Column('proxy_country', sa.String(), nullable=True),
        sa.Column('validation_status', sa.String(), nullable=True),
        sa.Column('last_validation_at', sa.DateTime(), nullable=True),
        sa.Column('validation_latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('neon_auth.users_sync.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_proxies_created_by', 'proxies', ['created_by'], unique=False)
    op.create_index('ix_proxies_validation_status', 'proxies', ['validation_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_proxies_validation_status', table_name='proxies')
    op.drop_index('ix_proxies_created_by', table_name='proxies')
    op.drop_table('proxies')
