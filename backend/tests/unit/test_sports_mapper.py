"""
Unit tests for Sports Mapper.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.core.event_mapping_layer.mappers.sports_mapper import SportsMapper
from app.core.scanner.models import CandidateMarket, Outcome, EventMetadata


@pytest.fixture
def sports_mapper():
    """Fixture para SportsMapper."""
    return SportsMapper()


@pytest.fixture
def nba_market():
    """Fixture para mercado NBA."""
    return CandidateMarket(
        polymarket_id="pm_nba",
        trace_id=uuid4(),
        question="Lakers vs Warriors - Who will win?",
        category="sports",
        subcategory="basketball",
        created_at=datetime.utcnow(),
        close_time=datetime.utcnow(),
        event_start_time=None,
        outcomes=[
            Outcome(name="YES", price=0.98, liquidity=1000.0, volume_24h=5000.0),
            Outcome(name="NO", price=0.02, liquidity=100.0, volume_24h=200.0)
        ],
        best_yes_price=0.98,
        best_no_price=0.02,
        spread=0.96,
        status="OPEN",
        event_metadata=EventMetadata(
            detected_teams=["Lakers", "Warriors"],
            detected_sport="basketball"
        ),
        volume_24h=5200.0,
        liquidity_total=1100.0,
        market_hash="test",
        scanned_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.mark.asyncio
async def test_map_nba_market(sports_mapper, nba_market):
    """Test mapping de mercado NBA."""
    trace_id = str(uuid4())
    descriptor = await sports_mapper.map(nba_market, trace_id)
    
    assert descriptor.market_id == "pm_nba"
    assert descriptor.event_type == "sports"
    assert isinstance(descriptor.mapping_confidence, float)
    assert 0.0 <= descriptor.mapping_confidence <= 1.0


@pytest.mark.asyncio
async def test_map_market_insufficient_teams(sports_mapper):
    """Test mapping con equipos insuficientes."""
    market = CandidateMarket(
        polymarket_id="pm_no_teams",
        trace_id=uuid4(),
        question="Will there be a game?",
        category="sports",
        created_at=datetime.utcnow(),
        outcomes=[
            Outcome(name="YES", price=0.50, liquidity=100.0, volume_24h=100.0),
            Outcome(name="NO", price=0.50, liquidity=100.0, volume_24h=100.0)
        ],
        best_yes_price=0.50,
        best_no_price=0.50,
        spread=0.0,
        status="OPEN",
        event_metadata=EventMetadata(),
        volume_24h=200.0,
        liquidity_total=200.0,
        market_hash="test",
        scanned_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    trace_id = str(uuid4())
    descriptor = await sports_mapper.map(market, trace_id)
    
    assert descriptor.mapped is False
    assert descriptor.reason == "insufficient_teams_detected"


def test_calculate_confidence(sports_mapper):
    """Test cálculo de confianza."""
    confidence = sports_mapper.calculate_confidence(
        entity_match_score=1.0,
        date_match_score=0.9,
        source_reliability_score=1.0
    )
    
    expected = 0.6 * 1.0 + 0.25 * 0.9 + 0.15 * 1.0
    assert abs(confidence - expected) < 0.01


def test_extract_teams_from_question(sports_mapper):
    """Test extracción de equipos desde pregunta."""
    market = CandidateMarket(
        polymarket_id="pm_test",
        trace_id=uuid4(),
        question="Lakers vs Warriors",
        category="sports",
        created_at=datetime.utcnow(),
        outcomes=[
            Outcome(name="YES", price=0.50, liquidity=100.0, volume_24h=100.0),
            Outcome(name="NO", price=0.50, liquidity=100.0, volume_24h=100.0)
        ],
        best_yes_price=0.50,
        best_no_price=0.50,
        spread=0.0,
        status="OPEN",
        event_metadata=EventMetadata(),
        volume_24h=200.0,
        liquidity_total=200.0,
        market_hash="test",
        scanned_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    teams = sports_mapper._extract_teams(market)
    assert len(teams) >= 2
    assert any("Lakers" in team for team in teams)
    assert any("Warriors" in team for team in teams)


def test_determine_sport_and_league_nba(sports_mapper):
    """Test determinación de deporte y liga NBA."""
    market = CandidateMarket(
        polymarket_id="pm_test",
        trace_id=uuid4(),
        question="Lakers vs Warriors",
        category="sports",
        subcategory="basketball",
        created_at=datetime.utcnow(),
        outcomes=[
            Outcome(name="YES", price=0.50, liquidity=100.0, volume_24h=100.0),
            Outcome(name="NO", price=0.50, liquidity=100.0, volume_24h=100.0)
        ],
        best_yes_price=0.50,
        best_no_price=0.50,
        spread=0.0,
        status="OPEN",
        event_metadata=EventMetadata(
            detected_teams=["Lakers", "Warriors"]
        ),
        volume_24h=200.0,
        liquidity_total=200.0,
        market_hash="test",
        scanned_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    sport, league = sports_mapper._determine_sport_and_league(
        ["Los Angeles Lakers", "Golden State Warriors"],
        market
    )
    
    assert sport == "basketball"
    assert league == "nba"


def test_calculate_team_match(sports_mapper):
    """Test cálculo de coincidencia de equipos."""
    # Coincidencia exacta
    score = sports_mapper._calculate_team_match(
        ["Lakers", "Warriors"],
        ["Lakers", "Warriors"]
    )
    assert score == 1.0
    
    # Coincidencia parcial
    score = sports_mapper._calculate_team_match(
        ["Lakers", "Warriors"],
        ["Lakers", "Celtics"]
    )
    assert 0.0 < score < 1.0
    
    # Sin coincidencia
    score = sports_mapper._calculate_team_match(
        ["Lakers", "Warriors"],
        ["Celtics", "Heat"]
    )
    assert score == 0.0


def test_calculate_date_match(sports_mapper):
    """Test cálculo de coincidencia de fechas."""
    from datetime import timedelta
    
    now = datetime.utcnow()
    
    # Misma fecha
    score = sports_mapper._calculate_date_match(now, now)
    assert score == 1.0
    
    # Diferencia de 1 hora
    score = sports_mapper._calculate_date_match(now, now + timedelta(hours=1))
    assert score == 1.0
    
    # Diferencia de 3 horas
    score = sports_mapper._calculate_date_match(now, now + timedelta(hours=3))
    assert 0.5 < score < 1.0
    
    # Diferencia de 1 semana
    score = sports_mapper._calculate_date_match(now, now + timedelta(days=7))
    assert score < 0.5

