"""
Tests adicionales para features (cobertura 100%).
"""
import pytest
from app.core.orderbook.features import (
    compute_depth_usdc_at_bps_buy,
    compute_impact_bps_for_usdc_buy,
    compute_replenishment_score,
)
from app.core.orderbook.models import OrderbookLevel


def test_features_depth_empty_asks():
    """Test depth calculation with empty asks."""
    asks = []
    best_ask = 0.50
    depth = compute_depth_usdc_at_bps_buy(asks, best_ask, 50)
    assert depth == 0.0


def test_features_depth_zero_best_ask():
    """Test depth calculation with zero best_ask."""
    asks = [OrderbookLevel(price=0.50, size=100)]
    best_ask = 0.0
    depth = compute_depth_usdc_at_bps_buy(asks, best_ask, 50)
    assert depth == 0.0


def test_features_impact_empty_asks():
    """Test impact calculation with empty asks."""
    asks = []
    best_ask = 0.50
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 100.0)
    assert impact == 0.0


def test_features_impact_zero_best_ask():
    """Test impact calculation with zero best_ask."""
    asks = [OrderbookLevel(price=0.50, size=100)]
    best_ask = 0.0
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 100.0)
    assert impact == 0.0


def test_features_impact_zero_target():
    """Test impact calculation with zero target_usdc."""
    asks = [OrderbookLevel(price=0.50, size=100)]
    best_ask = 0.50
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 0.0)
    assert impact == 0.0


def test_features_replenishment_score():
    """Test replenishment score calculation."""
    depth_history = [100.0, 120.0, 150.0]
    baseline_depth = 100.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    # Current depth = 150, baseline = 100
    # delta_positive = 50, score = 50/100 = 0.5
    assert score == pytest.approx(0.5, abs=0.01)


def test_features_replenishment_score_empty_history():
    """Test replenishment score with empty history."""
    depth_history = []
    baseline_depth = 100.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    assert score == 0.0


def test_features_replenishment_score_zero_baseline():
    """Test replenishment score with zero baseline."""
    depth_history = [100.0, 120.0]
    baseline_depth = 0.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    assert score == 0.0


def test_features_replenishment_score_decreasing():
    """Test replenishment score with decreasing depth."""
    depth_history = [150.0, 120.0, 100.0]
    baseline_depth = 150.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    # Current depth = 100, baseline = 150
    # delta_positive = max(0, 100-150) = 0
    assert score == 0.0


def test_features_replenishment_score_clamp():
    """Test replenishment score clamping to 1.0."""
    depth_history = [100.0, 300.0]  # 3x baseline
    baseline_depth = 100.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    # Should be clamped to 1.0
    assert score == 1.0


def test_features_spread_bps_zero_bid():
    """Test spread calculation with zero bid."""
    from app.core.orderbook.features import compute_spread_bps
    spread = compute_spread_bps(0.0, 0.52)
    assert spread == 0.0


def test_features_update_rate_hz_empty_timestamps():
    """Test update rate with empty timestamps."""
    from app.core.orderbook.features import compute_update_rate_hz
    rate = compute_update_rate_hz([], window_seconds=10)
    assert rate == 0.0


def test_features_update_rate_hz_single_timestamp():
    """Test update rate with single timestamp."""
    from app.core.orderbook.features import compute_update_rate_hz
    rate = compute_update_rate_hz([1000], window_seconds=10)
    assert rate == 0.0


def test_features_update_rate_hz_zero_timespan():
    """Test update rate with zero time span."""
    from app.core.orderbook.features import compute_update_rate_hz
    timestamps = [1000, 1000]  # Same timestamp
    rate = compute_update_rate_hz(timestamps, window_seconds=10)
    assert rate == 0.0


def test_features_impact_zero_shares():
    """Test impact when total_shares_filled is zero."""
    asks = [
        OrderbookLevel(price=0.50, size=0.0),  # Zero size
    ]
    best_ask = 0.50
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 100.0)
    # Con size=0, no puede gastar 100 USDC, así que retorna 1e9 (insufficient depth)
    assert impact == 1e9


def test_features_impact_break_early():
    """Test impact when break early (total_usdc_spent >= target_usdc)."""
    asks = [
        OrderbookLevel(price=0.50, size=100),  # 50 USDC
        OrderbookLevel(price=0.51, size=100),  # 51 USDC
    ]
    best_ask = 0.50
    # Target pequeño que se completa en el primer nivel
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 25.0)
    # Debe completarse en el primer nivel, impact = 0
    assert impact == 0.0


def test_features_impact_exact_target():
    """Test impact when target_usdc is exactly spent (covers break early)."""
    asks = [
        OrderbookLevel(price=0.50, size=100),  # 50 USDC
    ]
    best_ask = 0.50
    # Target exacto que se completa exactamente
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 50.0)
    # Debe completarse exactamente, impact = 0
    assert impact == 0.0


def test_features_impact_zero_price_level():
    """Test impact when a level has zero price (should skip it)."""
    asks = [
        OrderbookLevel(price=0.0, size=100),  # Zero price (invalid, should skip)
        OrderbookLevel(price=0.50, size=100),  # Valid
    ]
    best_ask = 0.50
    impact = compute_impact_bps_for_usdc_buy(asks, best_ask, 50.0)
    # Debe usar solo el segundo nivel, impact = 0
    assert impact == 0.0


def test_features_concentration_zero_total():
    """Test concentration when total_usdc_topn is zero."""
    from app.core.orderbook.features import compute_concentration_top3_pct_buy
    asks = [
        OrderbookLevel(price=0.50, size=0.0),  # Zero size
    ]
    concentration = compute_concentration_top3_pct_buy(asks)
    assert concentration == 0.0


def test_features_replenishment_score_zero_current():
    """Test replenishment score when current_depth is zero."""
    depth_history = [100.0, 0.0]  # Current depth = 0
    baseline_depth = 100.0
    
    score = compute_replenishment_score(depth_history, baseline_depth)
    assert score == 0.0

