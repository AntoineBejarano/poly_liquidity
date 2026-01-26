"""
Unit tests for Scanner Filters.
"""
import pytest
from app.core.scanner.filters import ScannerFilters
from app.core.state import RiskConfig


@pytest.fixture
def risk_config():
    """Fixture para RiskConfig."""
    config = RiskConfig()
    config.min_price_threshold = 0.97
    config.allowed_categories = ["sports"]
    config.allowed_subcategories = []
    return config


@pytest.fixture
def scanner_filters(risk_config):
    """Fixture para ScannerFilters."""
    return ScannerFilters(config=risk_config)


def test_filter_structural_passes_valid_market(scanner_filters):
    """Test que filtros estructurales pasan mercado válido."""
    market = {
        "id": "pm123",
        "status": "OPEN",
        "outcomes": [
            {"name": "YES", "price": 0.98},
            {"name": "NO", "price": 0.02}
        ]
    }
    
    passes, reason = scanner_filters.filter_structural(market)
    assert passes is True
    assert reason is None


def test_filter_structural_rejects_closed_market(scanner_filters):
    """Test que filtros estructurales rechazan mercado cerrado."""
    market = {
        "id": "pm123",
        "status": "CLOSED",
        "outcomes": [
            {"name": "YES", "price": 0.98},
            {"name": "NO", "price": 0.02}
        ]
    }
    
    passes, reason = scanner_filters.filter_structural(market)
    assert passes is False
    assert "not OPEN" in reason


def test_filter_structural_rejects_non_binary_market(scanner_filters):
    """Test que filtros estructurales rechazan mercado no binario."""
    market = {
        "id": "pm123",
        "status": "OPEN",
        "outcomes": [
            {"name": "YES", "price": 0.98}
        ]
    }
    
    passes, reason = scanner_filters.filter_structural(market)
    assert passes is False
    assert "outcomes" in reason.lower()


def test_filter_category_passes_sports(scanner_filters):
    """Test que filtro de categoría pasa sports."""
    market = {
        "category": "sports",
        "subcategory": "basketball"
    }
    
    passes, reason = scanner_filters.filter_category(market)
    assert passes is True
    assert reason is None


def test_filter_category_rejects_non_sports(scanner_filters):
    """Test que filtro de categoría rechaza no-sports."""
    market = {
        "category": "politics"
    }
    
    passes, reason = scanner_filters.filter_category(market)
    assert passes is False
    assert "not in allowed categories" in reason


def test_filter_price_passes_above_threshold(scanner_filters):
    """Test que filtro de precio pasa precio por encima del umbral."""
    market = {
        "outcomes": [
            {"name": "YES", "price": 0.98},
            {"name": "NO", "price": 0.02}
        ]
    }
    
    passes, reason = scanner_filters.filter_price(market)
    assert passes is True
    assert reason is None


def test_filter_price_rejects_below_threshold(scanner_filters):
    """Test que filtro de precio rechaza precio por debajo del umbral."""
    market = {
        "outcomes": [
            {"name": "YES", "price": 0.96},  # < 0.97
            {"name": "NO", "price": 0.04}
        ]
    }
    
    passes, reason = scanner_filters.filter_price(market)
    assert passes is False
    assert "threshold" in reason.lower()


def test_apply_all_filters_passes_valid_market(scanner_filters):
    """Test que apply_all_filters pasa mercado válido."""
    market = {
        "id": "pm123",
        "status": "OPEN",
        "category": "sports",
        "outcomes": [
            {"name": "YES", "price": 0.98},
            {"name": "NO", "price": 0.02}
        ]
    }
    
    passes, reason = scanner_filters.apply_all_filters(market)
    assert passes is True
    assert reason is None


def test_apply_all_filters_rejects_invalid_market(scanner_filters):
    """Test que apply_all_filters rechaza mercado inválido."""
    market = {
        "id": "pm123",
        "status": "CLOSED",  # Inválido
        "category": "sports",
        "outcomes": [
            {"name": "YES", "price": 0.98},
            {"name": "NO", "price": 0.02}
        ]
    }
    
    passes, reason = scanner_filters.apply_all_filters(market)
    assert passes is False
    assert reason is not None

