"""
Unit tests for Scanner Normalizer.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from app.core.scanner.normalizer import ScannerNormalizer
from app.core.scanner.models import Outcome, EventMetadata


@pytest.fixture
def normalizer():
    """Fixture para ScannerNormalizer."""
    return ScannerNormalizer()


def test_normalize_outcome_name(normalizer):
    """Test normalización de nombres de outcomes."""
    assert normalizer.normalize_outcome_name("Yes") == "YES"
    assert normalizer.normalize_outcome_name("No") == "NO"
    assert normalizer.normalize_outcome_name("True") == "YES"
    assert normalizer.normalize_outcome_name("False") == "NO"
    assert normalizer.normalize_outcome_name("YES") == "YES"


def test_normalize_outcomes(normalizer):
    """Test normalización de outcomes."""
    outcomes_raw = [
        {"name": "Yes", "price": 0.98, "liquidity": 1000.0, "volume_24h": 5000.0},
        {"name": "No", "price": 0.02, "liquidity": 100.0, "volume_24h": 200.0}
    ]
    
    outcomes = normalizer.normalize_outcomes(outcomes_raw)
    
    assert len(outcomes) == 2
    assert outcomes[0].name == "YES"
    assert outcomes[0].price == 0.98
    assert outcomes[1].name == "NO"
    assert outcomes[1].price == 0.02
    
    # Deben estar ordenados por precio (mayor a menor)
    assert outcomes[0].price > outcomes[1].price


def test_normalize_category(normalizer):
    """Test normalización de categoría."""
    assert normalizer.normalize_category("Sports") == "sports"
    assert normalizer.normalize_category("  SPORTS  ") == "sports"
    assert normalizer.normalize_category(None) == "unknown"


def test_extract_event_metadata_teams(normalizer):
    """Test extracción de equipos desde metadata."""
    question = "Lakers vs Celtics - Who will win?"
    metadata = normalizer.extract_event_metadata(question)
    
    assert len(metadata.detected_teams) > 0
    assert "Lakers" in metadata.detected_teams or "Celtics" in metadata.detected_teams


def test_extract_event_metadata_sport(normalizer):
    """Test detección de deporte."""
    question = "Lakers vs Celtics NBA game"
    metadata = normalizer.extract_event_metadata(question)
    
    assert metadata.detected_sport == "basketball"


def test_calculate_market_hash(normalizer):
    """Test cálculo de hash de mercado."""
    outcomes = [
        Outcome(name="YES", price=0.98, liquidity=1000.0, volume_24h=5000.0),
        Outcome(name="NO", price=0.02, liquidity=100.0, volume_24h=200.0)
    ]
    
    hash1 = normalizer.calculate_market_hash("pm123", "Test question", outcomes)
    hash2 = normalizer.calculate_market_hash("pm123", "Test question", outcomes)
    
    # Mismo input debe dar mismo hash
    assert hash1 == hash2
    
    # Diferente input debe dar diferente hash
    hash3 = normalizer.calculate_market_hash("pm456", "Test question", outcomes)
    assert hash1 != hash3


def test_normalize_market(normalizer):
    """Test normalización completa de mercado."""
    trace_id = str(uuid4())
    market = {
        "id": "pm123",
        "question": "Lakers vs Celtics - Who will win?",
        "description": "NBA game",
        "category": "Sports",
        "subcategory": "Basketball",
        "status": "OPEN",
        "outcomes": [
            {"name": "Yes", "price": 0.98, "liquidity": 1000.0, "volume_24h": 5000.0},
            {"name": "No", "price": 0.02, "liquidity": 100.0, "volume_24h": 200.0}
        ],
        "created_at": datetime.utcnow()
    }
    
    candidate = normalizer.normalize_market(market, trace_id)
    
    assert candidate.polymarket_id == "pm123"
    assert candidate.question == "Lakers vs Celtics - Who will win?"
    assert candidate.category == "sports"
    assert candidate.subcategory == "basketball"
    assert len(candidate.outcomes) == 2
    assert candidate.outcomes[0].name == "YES"
    assert candidate.outcomes[1].name == "NO"
    assert candidate.best_yes_price == 0.98
    assert candidate.best_no_price == 0.02
    assert candidate.spread == 0.96
    assert candidate.trace_id == trace_id
    assert candidate.market_hash is not None

