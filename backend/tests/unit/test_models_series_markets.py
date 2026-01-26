"""
Tests para modelos Series, Market, Event, Tag, MarketTag.

Verifica:
- Creación de modelos
- Relaciones entre modelos
- Validaciones de campos
- Que NO se use 'metadata' como nombre de columna (colisión con Base.metadata)
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.series import Series
from app.models.market import Market
from app.models.event import Event
from app.models.tag import Tag
from app.models.market_tag import MarketTag


@pytest.fixture(scope="function")
def isolated_db_session():
    """
    Create an isolated test database session with only our models.
    This avoids issues with missing tables like execution_session.
    
    Includes related tables (orders, positions, trades, exposures) because
    Market has cascade relationships that SQLAlchemy will try to load.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create only the tables we need for these tests
    # Include orders, positions, trades, exposures because Market has cascade relationships
    tables_to_create = [
        Base.metadata.tables['series'],
        Base.metadata.tables['tags'],
        Base.metadata.tables['markets'],
        Base.metadata.tables['events'],
        Base.metadata.tables['market_tags'],
    ]
    # Add related tables if they exist (for cascade delete tests)
    for table_name in ['orders', 'positions', 'trades', 'exposures']:
        if table_name in Base.metadata.tables:
            tables_to_create.append(Base.metadata.tables[table_name])
    
    Base.metadata.create_all(engine, tables=tables_to_create)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop in reverse order
        Base.metadata.drop_all(engine, tables=reversed(tables_to_create))


class TestSeries:
    """Tests para modelo Series."""
    
    def test_create_series(self, isolated_db_session):
        """Test crear una Series básica."""
        series = Series(
            polymarket_series_id="series-btc-up-down",
            name="Bitcoin Up or Down",
            slug="bitcoin-up-or-down",
            description="Series de markets BTC Up/Down",
            series_type="recurring",
            recurrence="15m",
            polymarket_payload={"raw": "data"}
        )
        isolated_db_session.add(series)
        isolated_db_session.commit()
        
        assert series.id is not None
        assert series.polymarket_series_id == "series-btc-up-down"
        assert series.name == "Bitcoin Up or Down"
        assert series.polymarket_payload == {"raw": "data"}
        assert hasattr(series, 'polymarket_payload')  # Debe tener 'polymarket_payload'
        # Nota: 'metadata' es un atributo de SQLAlchemy Base (no es una columna)
        # Verificamos que la columna se llama 'polymarket_payload' revisando el modelo
        assert hasattr(Series, '__table__')
        assert 'polymarket_payload' in Series.__table__.columns
        assert 'metadata' not in Series.__table__.columns  # Verificar que NO es una columna
    
    def test_series_unique_polymarket_id(self, isolated_db_session):
        """Test que polymarket_series_id sea único."""
        series1 = Series(
            polymarket_series_id="series-1",
            name="Series 1"
        )
        isolated_db_session.add(series1)
        isolated_db_session.commit()
        
        series2 = Series(
            polymarket_series_id="series-1",  # Mismo ID
            name="Series 2"
        )
        isolated_db_session.add(series2)
        
        with pytest.raises(IntegrityError):
            isolated_db_session.commit()
    
    def test_series_optional_fields(self, isolated_db_session):
        """Test que series_type y recurrence sean opcionales (best-effort)."""
        series = Series(
            polymarket_series_id="series-minimal",
            name="Minimal Series"
            # Sin series_type ni recurrence
        )
        isolated_db_session.add(series)
        isolated_db_session.commit()
        
        assert series.series_type is None
        assert series.recurrence is None


class TestMarket:
    """Tests para modelo Market."""
    
    def test_create_market(self, isolated_db_session):
        """Test crear un Market básico."""
        market = Market(
            polymarket_id="market-btc-15m",
            name="BTC Up or Down – 15 min",
            category="crypto",
            enabled=False,
            polymarket_payload={"condition_id": "0x123"}
        )
        isolated_db_session.add(market)
        isolated_db_session.commit()
        
        assert market.id is not None
        assert market.polymarket_id == "market-btc-15m"
        assert market.name == "BTC Up or Down – 15 min"
        assert market.enabled is False
        assert hasattr(market, 'polymarket_payload')  # Debe tener 'polymarket_payload'
        # Verificar que la columna se llama 'polymarket_payload' y NO 'metadata'
        assert hasattr(Market, '__table__')
        assert 'polymarket_payload' in Market.__table__.columns
        assert 'metadata' not in Market.__table__.columns  # Verificar que NO es una columna
    
    def test_market_with_series(self, isolated_db_session):
        """Test Market con Series."""
        series = Series(
            polymarket_series_id="series-1",
            name="Test Series"
        )
        isolated_db_session.add(series)
        isolated_db_session.flush()
        
        market = Market(
            polymarket_id="market-1",
            name="Test Market",
            series_id=series.id
        )
        isolated_db_session.add(market)
        isolated_db_session.commit()
        
        assert market.series_id == series.id
        assert market.series == series
        assert market in series.markets
    
    def test_market_enabled_default(self, isolated_db_session):
        """Test que enabled tenga default False."""
        market = Market(
            polymarket_id="market-default",
            name="Default Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.commit()
        
        assert market.enabled is False


class TestEvent:
    """Tests para modelo Event."""
    
    def test_create_event(self, isolated_db_session):
        """Test crear un Event básico."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=15)
        
        event = Event(
            polymarket_event_id="event-123",
            market_id=market.id,
            start_time=start_time,
            end_time=end_time,
            state="UPCOMING",
            polymarket_payload={"question": "Will BTC go up?"}
        )
        isolated_db_session.add(event)
        isolated_db_session.commit()
        
        assert event.id is not None  # UUID interno
        assert event.polymarket_event_id == "event-123"  # ID de Polymarket
        assert event.market_id == market.id
        assert event.state == "UPCOMING"
        assert hasattr(event, 'polymarket_payload')  # Debe tener 'polymarket_payload'
        # Verificar que la columna se llama 'polymarket_payload' y NO 'metadata'
        assert hasattr(Event, '__table__')
        assert 'polymarket_payload' in Event.__table__.columns
        assert 'metadata' not in Event.__table__.columns  # Verificar que NO es una columna
        assert event.market == market
    
    def test_event_unique_polymarket_id(self, isolated_db_session):
        """Test que polymarket_event_id sea único."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=15)
        
        event1 = Event(
            polymarket_event_id="event-123",
            market_id=market.id,
            start_time=start_time,
            end_time=end_time
        )
        isolated_db_session.add(event1)
        isolated_db_session.commit()
        
        event2 = Event(
            polymarket_event_id="event-123",  # Mismo ID
            market_id=market.id,
            start_time=start_time,
            end_time=end_time
        )
        isolated_db_session.add(event2)
        
        with pytest.raises(IntegrityError):
            isolated_db_session.commit()
    
    def test_event_states(self, isolated_db_session):
        """Test diferentes estados de Event."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=15)
        
        states = ["UPCOMING", "ACTIVE", "FINISHED"]
        for state in states:
            event = Event(
                polymarket_event_id=f"event-{state.lower()}",
                market_id=market.id,
                start_time=start_time,
                end_time=end_time,
                state=state
            )
            isolated_db_session.add(event)
        
        isolated_db_session.commit()
        
        events = isolated_db_session.query(Event).filter(Event.market_id == market.id).all()
        assert len(events) == 3
        assert {e.state for e in events} == set(states)


class TestTag:
    """Tests para modelo Tag."""
    
    def test_create_tag(self, isolated_db_session):
        """Test crear un Tag básico."""
        tag = Tag(
            polymarket_tag_id="tag-crypto",
            name="crypto",
            slug="crypto",
            label="Cryptocurrency",
            polymarket_payload={"forceShow": True}
        )
        isolated_db_session.add(tag)
        isolated_db_session.commit()
        
        assert tag.id is not None
        assert tag.polymarket_tag_id == "tag-crypto"
        assert tag.name == "crypto"
        assert hasattr(tag, 'polymarket_payload')  # Debe tener 'polymarket_payload'
        # Verificar que la columna se llama 'polymarket_payload' y NO 'metadata'
        assert hasattr(Tag, '__table__')
        assert 'polymarket_payload' in Tag.__table__.columns
        assert 'metadata' not in Tag.__table__.columns  # Verificar que NO es una columna
    
    def test_tag_unique_polymarket_id(self, isolated_db_session):
        """Test que polymarket_tag_id sea único."""
        tag1 = Tag(
            polymarket_tag_id="tag-1",
            name="Tag 1"
        )
        isolated_db_session.add(tag1)
        isolated_db_session.commit()
        
        tag2 = Tag(
            polymarket_tag_id="tag-1",  # Mismo ID
            name="Tag 2"
        )
        isolated_db_session.add(tag2)
        
        with pytest.raises(IntegrityError):
            isolated_db_session.commit()


class TestMarketTag:
    """Tests para modelo MarketTag (relación many-to-many)."""
    
    def test_create_market_tag(self, isolated_db_session):
        """Test crear relación Market-Tag."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        tag = Tag(
            polymarket_tag_id="tag-1",
            name="crypto"
        )
        isolated_db_session.add(market)
        isolated_db_session.add(tag)
        isolated_db_session.flush()
        
        market_tag = MarketTag(
            market_id=market.id,
            tag_id=tag.id
        )
        isolated_db_session.add(market_tag)
        isolated_db_session.commit()
        
        assert market_tag.market == market
        assert market_tag.tag == tag
        assert market_tag in market.tags
        assert market_tag in tag.markets
    
    def test_market_multiple_tags(self, isolated_db_session):
        """Test que un Market pueda tener múltiples Tags."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        tags = [
            Tag(polymarket_tag_id=f"tag-{i}", name=f"tag{i}")
            for i in range(3)
        ]
        for tag in tags:
            isolated_db_session.add(tag)
        isolated_db_session.flush()
        
        for tag in tags:
            market_tag = MarketTag(
                market_id=market.id,
                tag_id=tag.id
            )
            isolated_db_session.add(market_tag)
        
        isolated_db_session.commit()
        
        assert len(market.tags) == 3
    
    def test_market_tag_unique_constraint(self, isolated_db_session):
        """Test que no se pueda duplicar la relación Market-Tag."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        tag = Tag(
            polymarket_tag_id="tag-1",
            name="crypto"
        )
        isolated_db_session.add(market)
        isolated_db_session.add(tag)
        isolated_db_session.flush()
        
        market_tag1 = MarketTag(
            market_id=market.id,
            tag_id=tag.id
        )
        isolated_db_session.add(market_tag1)
        isolated_db_session.commit()
        
        market_tag2 = MarketTag(
            market_id=market.id,
            tag_id=tag.id  # Misma relación
        )
        isolated_db_session.add(market_tag2)
        
        with pytest.raises(IntegrityError):
            isolated_db_session.commit()


class TestRelationships:
    """Tests para relaciones entre modelos."""
    
    def test_series_markets_relationship(self, isolated_db_session):
        """Test relación Series → Markets."""
        series = Series(
            polymarket_series_id="series-1",
            name="Test Series"
        )
        isolated_db_session.add(series)
        isolated_db_session.flush()
        
        markets = [
            Market(
                polymarket_id=f"market-{i}",
                name=f"Market {i}",
                series_id=series.id
            )
            for i in range(3)
        ]
        for market in markets:
            isolated_db_session.add(market)
        
        isolated_db_session.commit()
        
        assert len(series.markets) == 3
        for market in markets:
            assert market.series == series
    
    def test_market_events_relationship(self, isolated_db_session):
        """Test relación Market → Events."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        start_time = datetime.utcnow()
        events = []
        for i in range(3):
            event = Event(
                polymarket_event_id=f"event-{i}",
                market_id=market.id,
                start_time=start_time + timedelta(minutes=i*15),
                end_time=start_time + timedelta(minutes=(i+1)*15),
                state="UPCOMING"
            )
            events.append(event)
            isolated_db_session.add(event)
        
        isolated_db_session.commit()
        
        assert len(market.events) == 3
        for event in events:
            assert event.market == market
    
    def test_market_tags_relationship(self, isolated_db_session):
        """Test relación Market ↔ Tags (many-to-many)."""
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        tags = [
            Tag(polymarket_tag_id=f"tag-{i}", name=f"tag{i}")
            for i in range(2)
        ]
        
        isolated_db_session.add(market)
        for tag in tags:
            isolated_db_session.add(tag)
        isolated_db_session.flush()
        
        for tag in tags:
            market_tag = MarketTag(
                market_id=market.id,
                tag_id=tag.id
            )
            isolated_db_session.add(market_tag)
        
        isolated_db_session.commit()
        
        assert len(market.tags) == 2
        for tag in tags:
            assert len(tag.markets) == 1
    
    def test_cascade_delete(self, isolated_db_session):
        """
        Test que al eliminar Market se eliminen Events (cascade).
        
        Nota: No probamos eliminar Series porque la relación Series → Markets
        está configurada con cascade="save-update, merge" (no delete) para evitar
        eliminar markets que pueden tener órdenes, posiciones, etc.
        El cascade de Market → Events está configurado como "all, delete-orphan".
        """
        market = Market(
            polymarket_id="market-1",
            name="Test Market"
        )
        isolated_db_session.add(market)
        isolated_db_session.flush()
        
        event1 = Event(
            polymarket_event_id="event-1",
            market_id=market.id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(minutes=15)
        )
        event2 = Event(
            polymarket_event_id="event-2",
            market_id=market.id,
            start_time=datetime.utcnow() + timedelta(minutes=15),
            end_time=datetime.utcnow() + timedelta(minutes=30)
        )
        isolated_db_session.add(event1)
        isolated_db_session.add(event2)
        isolated_db_session.commit()
        
        # Verificar que los events existen
        assert len(market.events) == 2
        
        # Eliminar market debería eliminar events (cascade)
        isolated_db_session.delete(market)
        isolated_db_session.commit()
        
        # Events deberían estar eliminados (cascade desde Market)
        event1_check = isolated_db_session.query(Event).filter(Event.id == event1.id).first()
        event2_check = isolated_db_session.query(Event).filter(Event.id == event2.id).first()
        assert event1_check is None
        assert event2_check is None

