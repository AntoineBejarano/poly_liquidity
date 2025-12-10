"""Initial migration: create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-12 19:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_metadata table
    # Note: The actual user data comes from neon_auth.users_sync (managed by Stack Auth)
    # This table only stores additional metadata like roles
    op.create_table(
        'user_metadata',
        sa.Column('user_id', sa.String(), primary_key=True),
        sa.Column('role', sa.String(), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    # Add foreign key constraint to neon_auth.users_sync
    # Note: The table neon_auth.users_sync is managed by Stack Auth and already exists
    op.execute("""
        ALTER TABLE user_metadata 
        ADD CONSTRAINT fk_user_metadata_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES neon_auth.users_sync(id)
    """)
    
    # Create wallets table
    op.create_table(
        'wallets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False, index=True),
        sa.Column('encrypted_private_key', sa.LargeBinary(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create markets table
    op.create_table(
        'markets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('polymarket_id', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('question', sa.String(), nullable=False),
        sa.Column('outcome', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='OPEN'),
        sa.Column('last_price', sa.Float(), nullable=True),
        sa.Column('resolution_outcome', sa.String(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('markets.id'), nullable=False, index=True),
        sa.Column('external_event_id', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=False, server_default='LIVE'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('feed_a_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('feed_b_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create secrets table
    op.create_table(
        'secrets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create event_checkers table
    op.create_table(
        'event_checkers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('implementation_key', sa.String(), nullable=False, index=True),
        sa.Column('category', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create checker_configs table
    op.create_table(
        'checker_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('checker_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('event_checkers.id'), nullable=False, index=True),
        sa.Column('secret_name', sa.String(), sa.ForeignKey('secrets.name'), nullable=True),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('timeout_seconds', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('polymarket_order_id', sa.String(), nullable=True, index=True),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('markets.id'), nullable=False, index=True),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='NEW'),
        sa.Column('filled_size', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False, index=True),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('markets.id'), nullable=False, index=True),
        sa.Column('fill_price', sa.Float(), nullable=False),
        sa.Column('fill_size', sa.Float(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('markets.id'), nullable=False, unique=True, index=True),
        sa.Column('size', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_price', sa.Float(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payout', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create exposures table
    op.create_table(
        'exposures',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('markets.id'), nullable=False, index=True),
        sa.Column('notional', sa.Float(), nullable=False),
        sa.Column('max_allowed', sa.Float(), nullable=False),
        sa.Column('breached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create system_config table
    op.create_table(
        'system_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),  # References neon_auth.users_sync.id
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    # Add foreign key constraint to neon_auth.users_sync for updated_by
    op.execute("""
        ALTER TABLE system_config 
        ADD CONSTRAINT fk_system_config_updated_by 
        FOREIGN KEY (updated_by) 
        REFERENCES neon_auth.users_sync(id)
    """)
    
    # Insert default system configuration values
    from datetime import datetime
    import uuid
    
    default_configs = [
        {'key': 'tick_seconds', 'value': '1.0', 'value_type': 'float', 'category': 'system', 'description': 'Intervalo entre ticks del loop principal'},
        {'key': 'scan_interval_seconds', 'value': '30.0', 'value_type': 'float', 'category': 'scanner', 'description': 'Intervalo entre escaneos de mercados'},
        {'key': 'min_candidate_price', 'value': '0.97', 'value_type': 'float', 'category': 'scanner', 'description': 'Precio mínimo para considerar candidato'},
        {'key': 'min_feed_confidence', 'value': '0.8', 'value_type': 'float', 'category': 'event_engine', 'description': 'Confianza mínima requerida de un checker'},
        {'key': 'checker_timeout_seconds', 'value': '5.0', 'value_type': 'float', 'category': 'event_engine', 'description': 'Timeout máximo para ejecutar un checker'},
        {'key': 'max_exposure_per_market', 'value': '50000.0', 'value_type': 'float', 'category': 'risk', 'description': 'Exposición máxima por mercado (USDC)'},
        {'key': 'max_global_exposure', 'value': '500000.0', 'value_type': 'float', 'category': 'risk', 'description': 'Exposición global máxima (USDC)'},
        {'key': 'max_markets_active', 'value': '30', 'value_type': 'int', 'category': 'risk', 'description': 'Número máximo de mercados activos'},
        {'key': 'min_entry_price', 'value': '0.98', 'value_type': 'float', 'category': 'risk', 'description': 'Precio mínimo de entrada'},
        {'key': 'target_margin', 'value': '0.001', 'value_type': 'float', 'category': 'risk', 'description': 'Margen objetivo hacia 1.0'},
        {'key': 'safety_tick', 'value': '0.0001', 'value_type': 'float', 'category': 'risk', 'description': 'Descuento del best ask'},
        {'key': 'max_single_order_size', 'value': '10000.0', 'value_type': 'float', 'category': 'risk', 'description': 'Tamaño máximo de orden (USDC)'},
    ]
    
    now = datetime.utcnow()
    config_rows = [
        {
            'id': uuid.uuid4(),
            'key': config['key'],
            'value': config['value'],
            'value_type': config['value_type'],
            'category': config['category'],
            'description': config['description'],
            'created_at': now,
            'updated_at': now,
        }
        for config in default_configs
    ]
    
    op.bulk_insert(
        sa.table(
            'system_config',
            sa.column('id', postgresql.UUID(as_uuid=True)),
            sa.column('key', sa.String()),
            sa.column('value', sa.Text()),
            sa.column('value_type', sa.String()),
            sa.column('category', sa.String()),
            sa.column('description', sa.String()),
            sa.column('created_at', sa.DateTime()),
            sa.column('updated_at', sa.DateTime()),
        ),
        config_rows
    )


def downgrade() -> None:
    op.drop_table('system_config')
    op.drop_table('exposures')
    op.drop_table('positions')
    op.drop_table('trades')
    op.drop_table('orders')
    op.drop_table('checker_configs')
    op.drop_table('event_checkers')
    op.drop_table('secrets')
    op.drop_table('events')
    op.drop_table('markets')
    op.drop_table('wallets')
    op.drop_table('user_metadata')

