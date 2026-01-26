"""
Unit tests for Sports Classifier.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.core.event_mapping_layer.classifiers.sports_classifier import SportsClassifier
from app.core.scanner.models import CandidateMarket, Outcome, EventMetadata


@pytest.fixture
def sports_classifier():
    """Fixture para SportsClassifier."""
    return SportsClassifier()


@pytest.fixture
def sports_market():
    """Fixture para mercado deportivo."""
    return CandidateMarket(
        polymarket_id="pm_sports",
        trace_id=uuid4(),
        question="Lakers vs Warriors - Who will win?",
        category="sports",
        subcategory="basketball",
        created_at=datetime.utcnow(),
        outcomes=[
            Outcome(name="YES", price=0.98, liquidity=100.0, volume_24h=100.0),
            Outcome(name="NO", price=0.02, liquidity=10.0, volume_24h=10.0)
        ],
        best_yes_price=0.98,
        best_no_price=0.02,
        spread=0.96,
        status="OPEN",
        event_metadata=EventMetadata(
            detected_teams=["Lakers", "Warriors"],
            detected_sport="basketball"
        ),
        volume_24h=110.0,
        liquidity_total=110.0,
        market_hash="test",
        scanned_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def test_classify_sports_by_category(sports_classifier, sports_market):
    """Test clasificación por categoría."""
    event_type = sports_classifier.classify(sports_market)
    assert event_type == "sports"


def test_classify_sports_by_pattern(sports_classifier):
    """Test clasificación por patrón."""
    market = CandidateMarket(
        polymarket_id="pm_test",
        trace_id=uuid4(),
        question="Team A vs Team B",
        category="unknown",
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
    
    event_type = sports_classifier.classify(market)
    assert event_type == "sports"


def test_classify_non_sports(sports_classifier):
    """Test que no clasifica como sports."""
    market = CandidateMarket(
        polymarket_id="pm_test",
        trace_id=uuid4(),
        question="Will it rain tomorrow?",
        category="weather",
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
    
    event_type = sports_classifier.classify(market)
    assert event_type == "unknown"


def test_get_confidence_high(sports_classifier, sports_market):
    """Test confianza alta para mercado deportivo claro."""
    confidence = sports_classifier.get_confidence(sports_market)
    assert confidence > 0.5
    assert 0.0 <= confidence <= 1.0


def test_get_confidence_low(sports_classifier):
    """Test confianza baja para mercado no deportivo."""
    market = CandidateMarket(
        polymarket_id="pm_test",
        trace_id=uuid4(),
        question="Random question",
        category="unknown",
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
    
    confidence = sports_classifier.get_confidence(market)
    assert confidence < 0.5

