"""Add Series, Markets, Events structure

Revision ID: 009_add_series_markets_events
Revises: 008_create_decision_trace
Create Date: 2025-01-15 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_add_series_markets_events'
down_revision = '008_create_decision_trace'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create series table
    op.create_table(
        'series',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('polymarket_series_id', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('series_type', sa.String(), nullable=True),  # best-effort
        sa.Column('recurrence', sa.String(), nullable=True),  # best-effort
        sa.Column('polymarket_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_series_polymarket_series_id', 'series', ['polymarket_series_id'])
    op.create_index('ix_series_slug', 'series', ['slug'])
    
    # 2. Create tags table
    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('polymarket_tag_id', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('polymarket_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_tags_polymarket_tag_id', 'tags', ['polymarket_tag_id'])
    op.create_index('ix_tags_slug', 'tags', ['slug'])
    
    # 3. Update markets table: add new columns and rename existing ones
    # Add new columns for Series/Markets structure
    op.add_column('markets', sa.Column('name', sa.String(), nullable=True))
    op.add_column('markets', sa.Column('category', sa.String(), nullable=True))
    op.add_column('markets', sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('markets', sa.Column('series_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('markets', sa.Column('polymarket_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Create indexes
    op.create_index('ix_markets_category', 'markets', ['category'])
    op.create_index('ix_markets_enabled', 'markets', ['enabled'])
    op.create_index('ix_markets_series_id', 'markets', ['series_id'])
    
    # Add foreign key for series_id
    op.create_foreign_key('fk_markets_series', 'markets', 'series', ['series_id'], ['id'])
    
    # Migrate data: if question exists, use it as name; if condition_id/clob_token_ids exist, move to polymarket_payload
    # Note: Using CAST to JSON since we're using JSON type, not JSONB
    op.execute("""
        UPDATE markets 
        SET name = COALESCE(question, polymarket_id),
            polymarket_payload = CAST(json_build_object(
                'condition_id', condition_id,
                'clob_token_ids', clob_token_ids,
                'question', question,
                'outcome', outcome
            ) AS JSON)
        WHERE name IS NULL
    """)
    
    # Make name NOT NULL after migration
    op.alter_column('markets', 'name', nullable=False)
    
    # 4. Create market_tags table (many-to-many relationship)
    op.create_table(
        'market_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('market_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['market_id'], ['markets.id'], name='fk_market_tags_market'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], name='fk_market_tags_tag'),
        sa.UniqueConstraint('market_id', 'tag_id', name='uq_market_tag'),
    )
    op.create_index('ix_market_tags_market_id', 'market_tags', ['market_id'])
    op.create_index('ix_market_tags_tag_id', 'market_tags', ['tag_id'])
    
    # 5. Update events table: migrate external_event_id to polymarket_event_id and add new columns
    # Add new columns
    op.add_column('events', sa.Column('polymarket_event_id', sa.String(), nullable=True))
    op.add_column('events', sa.Column('start_time', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('end_time', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('polymarket_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Migrate external_event_id to polymarket_event_id
    # Also migrate old state/confidence fields to polymarket_payload
    op.execute("""
        UPDATE events 
        SET polymarket_event_id = COALESCE(external_event_id, 'event_' || id::text),
            polymarket_payload = CAST(json_build_object(
                'old_state', state,
                'confidence', confidence,
                'feed_a_confirmed', feed_a_confirmed,
                'feed_b_confirmed', feed_b_confirmed,
                'finished_at', finished_at
            ) AS JSON)
        WHERE polymarket_event_id IS NULL
    """)
    
    # Create index for polymarket_event_id
    op.create_index('ix_events_polymarket_event_id', 'events', ['polymarket_event_id'])
    
    # Make polymarket_event_id unique and NOT NULL after migration
    op.alter_column('events', 'polymarket_event_id', nullable=False)
    op.create_unique_constraint('uq_events_polymarket_event_id', 'events', ['polymarket_event_id'])
    
    # Update state column: map old values to new ones (LIVE -> ACTIVE, etc.)
    op.execute("""
        UPDATE events 
        SET state = CASE 
            WHEN state = 'LIVE' THEN 'ACTIVE'
            WHEN state = 'FINISHED_UNCONFIRMED' THEN 'FINISHED'
            WHEN state = 'FINISHED_CONFIRMED' THEN 'FINISHED'
            ELSE 'UPCOMING'
        END
        WHERE state IN ('LIVE', 'FINISHED_UNCONFIRMED', 'FINISHED_CONFIRMED')
    """)


def downgrade() -> None:
    # Reverse order of upgrade
    
    # 5. Revert events table changes
    op.drop_constraint('uq_events_polymarket_event_id', 'events', type_='unique')
    op.drop_index('ix_events_polymarket_event_id', table_name='events')
    
    # Restore old fields from polymarket_payload if they exist
    op.execute("""
        UPDATE events 
        SET external_event_id = polymarket_event_id,
            state = COALESCE((polymarket_payload->>'old_state')::text, state),
            confidence = COALESCE((polymarket_payload->>'confidence')::float, confidence),
            feed_a_confirmed = COALESCE((polymarket_payload->>'feed_a_confirmed')::boolean, feed_a_confirmed),
            feed_b_confirmed = COALESCE((polymarket_payload->>'feed_b_confirmed')::boolean, feed_b_confirmed),
            finished_at = COALESCE(CAST((polymarket_payload->>'finished_at') AS timestamp), finished_at)
        WHERE polymarket_payload IS NOT NULL
    """)
    
    op.drop_column('events', 'polymarket_payload')
    op.drop_column('events', 'end_time')
    op.drop_column('events', 'start_time')
    op.drop_column('events', 'polymarket_event_id')
    
    # 4. Drop market_tags table
    op.drop_index('ix_market_tags_tag_id', table_name='market_tags')
    op.drop_index('ix_market_tags_market_id', table_name='market_tags')
    op.drop_table('market_tags')
    
    # 3. Revert markets table changes
    op.drop_constraint('fk_markets_series', 'markets', type_='foreignkey')
    op.drop_index('ix_markets_series_id', table_name='markets')
    op.drop_index('ix_markets_enabled', table_name='markets')
    op.drop_index('ix_markets_category', table_name='markets')
    
    # Extract data back from polymarket_payload if needed
    op.execute("""
        UPDATE markets 
        SET condition_id = (polymarket_payload->>'condition_id')::text,
            clob_token_ids = CAST((polymarket_payload->>'clob_token_ids') AS JSON)
        WHERE polymarket_payload IS NOT NULL
    """)
    
    op.drop_column('markets', 'polymarket_payload')
    op.drop_column('markets', 'series_id')
    op.drop_column('markets', 'enabled')
    op.drop_column('markets', 'category')
    op.drop_column('markets', 'name')
    
    # 2. Drop tags table
    op.drop_index('ix_tags_slug', table_name='tags')
    op.drop_index('ix_tags_polymarket_tag_id', table_name='tags')
    op.drop_table('tags')
    
    # 1. Drop series table
    op.drop_index('ix_series_slug', table_name='series')
    op.drop_index('ix_series_polymarket_series_id', table_name='series')
    op.drop_table('series')

