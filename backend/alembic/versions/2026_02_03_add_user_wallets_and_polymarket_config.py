"""add user_id to wallets and user_polymarket_config

Revision ID: 2026_02_03_wallets
Revises: b2c3d4e5f6a7
Create Date: 2026-02-03

- Añade user_id a wallets (FK neon_auth.users_sync) para que cada usuario tenga sus wallets.
- Crea tabla user_polymarket_config (user_id, polymarket_proxy_address, api_key, api_secret, api_passphrase)
  para credenciales Polymarket por usuario (guardadas en DB).
- Los FK a neon_auth.users_sync se crean solo si ese esquema/tabla existe (p. ej. con Stack Auth).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '2026_02_03_wallets'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    wallets_columns = [c["name"] for c in inspector.get_columns("wallets")]
    has_user_polymarket_config = "user_polymarket_config" in inspector.get_table_names()
    # No crear FK a neon_auth.users_sync aquí: en muchos entornos esa tabla no existe (Stack Auth).
    # Los modelos Wallet y UserPolymarketConfig definen la FK en SQLAlchemy; en producción con
    # Stack Auth se pueden añadir los constraints a mano o en una migración posterior.
    ref_exists = False

    # Añadir user_id a wallets (nullable para filas existentes)
    if "user_id" not in wallets_columns:
        op.add_column('wallets', sa.Column('user_id', sa.String(), nullable=True))
    if ref_exists:
        op.create_foreign_key(
            'fk_wallets_user_id',
            'wallets',
            'neon_auth.users_sync',
            ['user_id'],
            ['id']
        )
    try:
        op.create_index('ix_wallets_user_id', 'wallets', ['user_id'], unique=False)
    except Exception:
        pass

    # Tabla de configuración Polymarket por usuario (credenciales en DB)
    if not has_user_polymarket_config:
        op.create_table(
            'user_polymarket_config',
            sa.Column('user_id', sa.String(), primary_key=True, nullable=False),
            sa.Column('polymarket_proxy_address', sa.String(), nullable=True),
            sa.Column('api_key', sa.String(), nullable=True),
            sa.Column('api_secret', sa.String(), nullable=True),
            sa.Column('api_passphrase', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        if ref_exists:
            op.create_foreign_key(
                'fk_user_polymarket_config_user_id',
                'user_polymarket_config',
                'neon_auth.users_sync',
                ['user_id'],
                ['id']
            )


def downgrade() -> None:
    op.drop_table('user_polymarket_config')
    try:
        op.drop_constraint('fk_wallets_user_id', 'wallets', type_='foreignkey')
    except Exception:
        pass
    op.drop_index('ix_wallets_user_id', table_name='wallets', if_exists=True)
    op.drop_column('wallets', 'user_id')
