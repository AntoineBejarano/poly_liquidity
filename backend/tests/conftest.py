"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch

# Set environment variables BEFORE importing app modules
os.environ.setdefault("STACK_SECRET_SERVER_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Generate a valid Fernet key for testing
from cryptography.fernet import Fernet
_test_fernet_key = Fernet.generate_key().decode()
os.environ.setdefault("WALLET_ENCRYPTION_KEY", _test_fernet_key)

# Now import app modules
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.core.state import SystemState, RiskConfig
from app.core.config_service import SystemConfigService


# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a test database session.
    Uses SQLite in-memory database for fast tests.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Exclude UserSync table (uses schema which SQLite doesn't support)
    from app.models import UserSync
    from sqlalchemy import Table, Column, String, DateTime
    from sqlalchemy.dialects.postgresql import UUID
    metadata = Base.metadata
    
    # Create execution_session stub table for tests (needed by decision_trace FK)
    if 'execution_session' not in metadata.tables:
        execution_session_table = Table(
            'execution_session',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('session_name', String(255), nullable=False),
            Column('execution_mode', String(50), nullable=False),
            Column('started_at', DateTime, nullable=False),
            Column('ended_at', DateTime, nullable=True),
            Column('started_by', String(255), nullable=True),
            Column('config_snapshot', String, nullable=False),  # JSONB as String for SQLite
            Column('status', String(50), nullable=False),
            Column('metadata', String, nullable=True),  # JSONB as String for SQLite
            Column('created_at', DateTime, nullable=False),
            Column('updated_at', DateTime, nullable=False),
        )
    
    # Create all tables except UserSync
    metadata.create_all(engine, tables=[table for table in metadata.tables.values() if table.name != 'users_sync'])
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        metadata.drop_all(engine, tables=[table for table in metadata.tables.values() if table.name != 'users_sync'])


@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """Override get_db dependency for FastAPI tests."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    
    return _get_db


@pytest.fixture(scope="function")
def mock_state():
    """
    Create a mock SystemState for testing.
    Resets state between tests.
    """
    from app.core.state import state
    
    # Save original state
    original_markets = state.markets.copy()
    original_events = state.events.copy()
    original_exposures = state.exposures.copy()
    original_orders = state.orders.copy()
    original_positions = state.positions.copy()
    original_system_active = state.system_active
    original_risk_config = state.risk_config
    
    # Reset state
    state.markets.clear()
    state.events.clear()
    state.exposures.clear()
    state.orders.clear()
    state.positions.clear()
    state.system_active = True
    
    # Set default risk config
    state.risk_config = RiskConfig()
    state.risk_config.max_exposure_per_market = 10000.0
    state.risk_config.max_global_exposure = 50000.0
    state.risk_config.max_markets_active = 5
    state.risk_config.min_entry_price = 0.97
    state.risk_config.safety_tick = 0.001
    state.risk_config.target_margin = 0.01
    state.risk_config.max_single_order_size = 1000.0
    state.risk_config.tick_seconds = 1.0
    state.risk_config.scan_interval_seconds = 5.0
    
    yield state
    
    # Restore original state
    state.markets = original_markets
    state.events = original_events
    state.exposures = original_exposures
    state.orders = original_orders
    state.positions = original_positions
    state.system_active = original_system_active
    state.risk_config = original_risk_config


@pytest.fixture(scope="function")
def mock_config_service():
    """Mock config service for testing."""
    config = Mock(spec=SystemConfigService)
    config.get.return_value = 0.97  # min_candidate_price
    
    # Create RiskConfig properly (it doesn't accept parameters in __init__)
    risk_config = RiskConfig()
    risk_config.max_exposure_per_market = 10000.0
    risk_config.max_global_exposure = 50000.0
    risk_config.max_markets_active = 5
    risk_config.min_entry_price = 0.97
    risk_config.safety_tick = 0.001
    risk_config.target_margin = 0.01
    risk_config.max_single_order_size = 1000.0
    risk_config.tick_seconds = 1.0
    risk_config.scan_interval_seconds = 5.0
    # Scanner config
    risk_config.min_price_threshold = 0.97
    risk_config.allowed_categories = ["sports"]
    risk_config.allowed_subcategories = []
    
    config.get_risk_config.return_value = risk_config
    return config


@pytest.fixture(scope="function")
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing HTTP requests."""
    client = AsyncMock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"data": []}
    response.raise_for_status = Mock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.delete = AsyncMock(return_value=response)
    client.aclose = AsyncMock()
    return client


@pytest.fixture(scope="function")
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    rate_limiter = AsyncMock()
    rate_limiter.wait_for_capacity = AsyncMock(return_value=True)
    rate_limiter.record_violation = AsyncMock()
    return rate_limiter


@pytest.fixture(scope="function")
def mock_api_cache():
    """Mock API cache for testing."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.cleanup_expired = AsyncMock()
    return cache


@pytest.fixture(scope="function")
def mock_latency_monitor():
    """Mock latency monitor for testing."""
    from app.core.latency_monitor import LatencyStatus
    
    monitor = Mock()
    monitor.get_status.return_value = LatencyStatus.GREEN
    monitor.record_execution_latency = Mock()
    monitor.record_api_latency = Mock()
    return monitor


@pytest.fixture(scope="function")
def mock_wallet_service():
    """Mock wallet service for testing."""
    wallet_service = Mock()
    wallet_service.get_active_wallet.return_value = {
        "id": "test-wallet-id",
        "label": "Test Wallet",
        "address": "0x1234567890123456789012345678901234567890",
        "private_key": "0x" + "1" * 64,  # Mock private key
    }
    wallet_service.has_active_wallet.return_value = True
    wallet_service.set_active_wallet = Mock(return_value=True)
    wallet_service.invalidate_cache = Mock()
    return wallet_service


@pytest.fixture(scope="function")
def sample_market_data():
    """Sample market data for testing."""
    return {
        "id": "0x1234567890123456789012345678901234567890",
        "question": "Will Team A win?",
        "outcome_type": "BINARY",
        "status": "OPEN",
        "price": 0.98,
        "last_price": 0.98,
        "spread": 0.001,
        "volume": 10000.0,
        "orderbook": {
            "bids": [[0.979, 1000.0]],
            "asks": [[0.981, 1000.0]],
        },
    }


@pytest.fixture(scope="function")
def sample_event_data():
    """Sample event data for testing."""
    from uuid import uuid4
    return {
        "market_id": uuid4(),
        "external_event_id": "event-123",
        "state": "LIVE",
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    # Save original env
    original_env = os.environ.copy()
    
    # Set test environment
    os.environ.setdefault("WALLET_ENCRYPTION_KEY", "test-key-for-testing-only")
    
    yield
    
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)

