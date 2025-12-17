"""
Tests unitarios para StateCacheService.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.strategy_engine.state_cache_service import StateCacheService
from app.models.state_cache import StateCache
from app.models.base import Base


@pytest.fixture(scope="function")
def isolated_db_session():
    """
    Create an isolated test database session with only StateCache table.
    This avoids issues with missing tables like execution_session.
    SQLite doesn't support JSONB or UUID natively, so we use JSON and String.
    """
    from sqlalchemy import JSON, Table, Column, String, DateTime, MetaData, text
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create StateCache table manually with JSON instead of JSONB for SQLite
    # Use String for UUIDs since SQLite doesn't have native UUID support
    metadata = MetaData()
    state_cache_table = Table(
        'state_cache',
        metadata,
        Column('id', String, primary_key=True),  # String for UUID in SQLite
        Column('cache_key', String, nullable=False, unique=True),
        Column('cache_value', JSON, nullable=False),  # JSON instead of JSONB for SQLite
        Column('strategy_id', String, nullable=True),  # String for UUID in SQLite
        Column('event_id', String, nullable=True),  # String for UUID in SQLite
        Column('expires_at', DateTime, nullable=True),
        Column('created_at', DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP')),
        Column('updated_at', DateTime, nullable=True),
    )
    metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        metadata.drop_all(engine)


@pytest.fixture
def state_cache_service(isolated_db_session):
    """Fixture para StateCacheService."""
    return StateCacheService(isolated_db_session)


@pytest.mark.asyncio
async def test_get_set_basic(state_cache_service):
    """Test básico de get/set."""
    cache_key = "test.key"
    test_value = {"price": 0.98, "spread": 0.01}
    
    # Set
    await state_cache_service.set(cache_key, test_value)
    
    # Get
    result = await state_cache_service.get(cache_key)
    
    assert result == test_value


@pytest.mark.asyncio
async def test_get_nonexistent(state_cache_service):
    """Test que get retorna None para clave inexistente."""
    result = await state_cache_service.get("nonexistent.key")
    assert result is None


@pytest.mark.asyncio
async def test_set_with_ttl(state_cache_service):
    """Test set con TTL."""
    cache_key = "test.ttl"
    test_value = {"data": "test"}
    
    await state_cache_service.set(cache_key, test_value, ttl_seconds=60)
    
    result = await state_cache_service.get(cache_key)
    assert result == test_value
    
    # Verificar que está en memoria
    assert cache_key in state_cache_service._memory_cache


@pytest.mark.asyncio
async def test_get_from_db_when_not_in_memory(state_cache_service, isolated_db_session):
    """Test que get lee de DB cuando no está en memoria."""
    cache_key = "test.db"
    test_value = {"from": "db"}
    
    # Crear entrada directamente en DB
    cache_entry = StateCache(
        cache_key=cache_key,
        cache_value=test_value
    )
    isolated_db_session.add(cache_entry)
    isolated_db_session.commit()
    
    # Limpiar memoria
    state_cache_service._memory_cache.clear()
    
    # Get debería leer de DB
    result = await state_cache_service.get(cache_key)
    assert result == test_value
    
    # Debería estar ahora en memoria
    assert cache_key in state_cache_service._memory_cache


@pytest.mark.asyncio
async def test_expired_entry_removed(state_cache_service, isolated_db_session):
    """Test que entradas expiradas se eliminan."""
    cache_key = "test.expired"
    test_value = {"data": "test"}
    
    # Set con TTL muy corto
    await state_cache_service.set(cache_key, test_value, ttl_seconds=1)
    
    # Verificar que existe
    result = await state_cache_service.get(cache_key)
    assert result == test_value
    
    # Marcar como expirada tanto en memoria como en DB
    state_cache_service._memory_cache[cache_key] = (
        test_value,
        datetime.utcnow() - timedelta(seconds=1)
    )
    
    # También en DB
    cache_entry = isolated_db_session.query(StateCache).filter(
        StateCache.cache_key == cache_key
    ).first()
    if cache_entry:
        cache_entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        isolated_db_session.commit()
    
    # Get debería retornar None y eliminar de memoria y DB
    result = await state_cache_service.get(cache_key)
    assert result is None
    assert cache_key not in state_cache_service._memory_cache
    
    # Verificar que también se eliminó de DB
    cache_entry = isolated_db_session.query(StateCache).filter(
        StateCache.cache_key == cache_key
    ).first()
    assert cache_entry is None


@pytest.mark.asyncio
async def test_get_many_with_pattern(state_cache_service):
    """Test get_many con patrón."""
    # Crear múltiples entradas
    await state_cache_service.set("event.123.market_state", {"price": 0.98})
    await state_cache_service.set("event.123.event_state", {"state": "ACTIVE"})
    await state_cache_service.set("event.456.market_state", {"price": 0.99})
    await state_cache_service.set("strategy.789.config", {"setting": "value"})
    
    # Buscar todos los valores de event.123
    results = await state_cache_service.get_many("event.123.*")
    
    assert len(results) == 2
    assert "event.123.market_state" in results
    assert "event.123.event_state" in results
    assert "event.456.market_state" not in results


@pytest.mark.asyncio
async def test_get_many_all_events(state_cache_service):
    """Test get_many para todos los eventos."""
    await state_cache_service.set("event.123.market_state", {"price": 0.98})
    await state_cache_service.set("event.456.market_state", {"price": 0.99})
    await state_cache_service.set("event.789.event_state", {"state": "ACTIVE"})
    
    # Buscar todos los market_state de eventos
    results = await state_cache_service.get_many("event.*.market_state")
    
    assert len(results) == 2
    assert "event.123.market_state" in results
    assert "event.456.market_state" in results
    assert "event.789.event_state" not in results


@pytest.mark.asyncio
async def test_delete(state_cache_service, isolated_db_session):
    """Test delete."""
    cache_key = "test.delete"
    test_value = {"data": "test"}
    
    # Set
    await state_cache_service.set(cache_key, test_value)
    
    # Verificar que existe
    result = await state_cache_service.get(cache_key)
    assert result == test_value
    
    # Delete
    await state_cache_service.delete(cache_key)
    
    # Verificar que no existe
    result = await state_cache_service.get(cache_key)
    assert result is None
    
    # Verificar que no está en DB
    entry = isolated_db_session.query(StateCache).filter(
        StateCache.cache_key == cache_key
    ).first()
    assert entry is None


@pytest.mark.asyncio
async def test_clear_expired(state_cache_service, isolated_db_session):
    """Test clear_expired."""
    # Crear entradas expiradas y no expiradas
    await state_cache_service.set("test.expired1", {"data": "1"}, ttl_seconds=1)
    await state_cache_service.set("test.expired2", {"data": "2"}, ttl_seconds=1)
    await state_cache_service.set("test.valid", {"data": "3"}, ttl_seconds=3600)
    
    # Marcar como expiradas manualmente
    state_cache_service._memory_cache["test.expired1"] = (
        {"data": "1"},
        datetime.utcnow() - timedelta(seconds=10)
    )
    state_cache_service._memory_cache["test.expired2"] = (
        {"data": "2"},
        datetime.utcnow() - timedelta(seconds=10)
    )
    
    # También en DB
    expired_entry = isolated_db_session.query(StateCache).filter(
        StateCache.cache_key == "test.expired1"
    ).first()
    if expired_entry:
        expired_entry.expires_at = datetime.utcnow() - timedelta(seconds=10)
        isolated_db_session.commit()
    
    # Clear expired
    await state_cache_service.clear_expired()
    
    # Verificar que las expiradas fueron eliminadas
    assert "test.expired1" not in state_cache_service._memory_cache
    assert "test.expired2" not in state_cache_service._memory_cache
    assert "test.valid" in state_cache_service._memory_cache
    
    # Verificar que la válida sigue funcionando
    result = await state_cache_service.get("test.valid")
    assert result == {"data": "3"}


@pytest.mark.asyncio
async def test_set_with_strategy_and_event_id(state_cache_service, isolated_db_session):
    """Test set con strategy_id y event_id."""
    strategy_id = uuid4()
    event_id = uuid4()
    cache_key = "test.metadata"
    test_value = {"data": "test"}
    
    await state_cache_service.set(
        cache_key,
        test_value,
        strategy_id=strategy_id,
        event_id=event_id
    )
    
    # Verificar en DB
    entry = isolated_db_session.query(StateCache).filter(
        StateCache.cache_key == cache_key
    ).first()
    
    assert entry is not None
    assert entry.strategy_id == strategy_id
    assert entry.event_id == event_id

