"""
Tests unitarios para quorum dinámico en EventEngine y StateAggregator.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from app.core.event_engine import EventEngine
from app.core.event_watch_engine.state_aggregator import StateAggregator
from app.core.event_watch_engine.models import WatchEngineConfig, EventStateType
from app.core.checkers.base import CheckerResult
from app.core.checkers.health_service import CheckerHealthService


@pytest.fixture
def event_engine():
    """Fixture para EventEngine."""
    return EventEngine()


@pytest.fixture
def state_aggregator():
    """Fixture para StateAggregator."""
    config = WatchEngineConfig()
    return StateAggregator(config)


@pytest.fixture
def health_service():
    """Fixture para CheckerHealthService."""
    return CheckerHealthService()


def test_calculate_effective_quorum_with_2_checkers(event_engine):
    """Test que quorum efectivo es 2 cuando hay 2 checkers disponibles y quorum_base = 2."""
    quorum_base = 2
    available_checkers = 2
    allow_single_checker = False
    allow_zero_checker = False
    
    quorum_effective, reason, trading_permitted = event_engine._calculate_effective_quorum(
        quorum_base, available_checkers, allow_single_checker, allow_zero_checker
    )
    
    assert quorum_effective == 2
    assert reason == "quorum_base_applied"
    assert trading_permitted is True


def test_calculate_effective_quorum_with_1_checker_allow_single(event_engine):
    """Test que quorum efectivo es 1 cuando hay 1 checker y allow_single_checker = true."""
    quorum_base = 2
    available_checkers = 1
    allow_single_checker = True
    allow_zero_checker = False
    
    quorum_effective, reason, trading_permitted = event_engine._calculate_effective_quorum(
        quorum_base, available_checkers, allow_single_checker, allow_zero_checker
    )
    
    assert quorum_effective == 1
    assert reason == "single_checker_allowed"
    assert trading_permitted is True


def test_calculate_effective_quorum_with_0_checkers_allow_zero(event_engine):
    """Test que con 0 checkers y allow_zero_checker = true, no hay quorum pero sistema sigue vivo."""
    quorum_base = 2
    available_checkers = 0
    allow_single_checker = False
    allow_zero_checker = True
    
    quorum_effective, reason, trading_permitted = event_engine._calculate_effective_quorum(
        quorum_base, available_checkers, allow_single_checker, allow_zero_checker
    )
    
    assert quorum_effective is None
    assert reason == "no_checkers_available_allow_zero"
    assert trading_permitted is False


def test_calculate_effective_quorum_with_0_checkers_no_allow_zero(event_engine):
    """Test que con 0 checkers y allow_zero_checker = false, sistema está degradado."""
    quorum_base = 2
    available_checkers = 0
    allow_single_checker = False
    allow_zero_checker = False
    
    quorum_effective, reason, trading_permitted = event_engine._calculate_effective_quorum(
        quorum_base, available_checkers, allow_single_checker, allow_zero_checker
    )
    
    assert quorum_effective is None
    assert reason == "no_checkers_available_system_degraded"
    assert trading_permitted is False


@pytest.mark.asyncio
async def test_aggregate_checker_results_quorum_met(event_engine):
    """Test que FINISHED_CONFIRMED se emite cuando se cumple quorum."""
    # Simular 2 checkers con FINISHED
    results = [
        CheckerResult(
            state="FINISHED",
            confidence=0.9,
            source="checker1",
            timestamp=datetime.utcnow()
        ),
        CheckerResult(
            state="FINISHED",
            confidence=0.85,
            source="checker2",
            timestamp=datetime.utcnow()
        )
    ]
    
    healthy_checker_ids = ["checker1", "checker2"]
    
    state, confidence, metadata = await event_engine._aggregate_checker_results(
        results, "sports", healthy_checker_ids
    )
    
    assert state == "FINISHED_CONFIRMED"
    assert metadata["quorum_used"] == 2
    assert metadata["checkers_used"] == 2
    assert metadata["trading_permitted"] is True


@pytest.mark.asyncio
async def test_aggregate_checker_results_quorum_not_met(event_engine):
    """Test que FINISHED_UNCONFIRMED se emite cuando NO se cumple quorum."""
    # Simular 1 checker con FINISHED (quorum requiere 2)
    results = [
        CheckerResult(
            state="FINISHED",
            confidence=0.9,
            source="checker1",
            timestamp=datetime.utcnow()
        )
    ]
    
    healthy_checker_ids = ["checker1", "checker2"]  # 2 disponibles pero solo 1 usado
    
    state, confidence, metadata = await event_engine._aggregate_checker_results(
        results, "sports", healthy_checker_ids
    )
    
    assert state == "FINISHED_UNCONFIRMED"
    assert metadata["quorum_used"] == 2
    assert metadata["checkers_used"] == 1
    assert metadata["trading_permitted"] is True


@pytest.mark.asyncio
async def test_aggregate_checker_results_no_checkers_available(event_engine):
    """Test que UNKNOWN se emite cuando no hay checkers disponibles."""
    results = [
        CheckerResult(
            state="FINISHED",
            confidence=0.9,
            source="checker1",
            timestamp=datetime.utcnow()
        )
    ]
    
    healthy_checker_ids = []  # No hay checkers saludables
    
    state, confidence, metadata = await event_engine._aggregate_checker_results(
        results, "sports", healthy_checker_ids
    )
    
    assert state == "UNKNOWN"
    assert metadata["quorum_used"] is None
    assert metadata["trading_permitted"] is False

