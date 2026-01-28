"""
Tests unitarios para el Template Compiler (Near-Resolution).
"""
import pytest

from app.core.strategy_engine.template_compiler import compile_liquidity_near_end


class TestCompileLiquidityNearEnd:
    """Tests para compile_liquidity_near_end."""

    def test_graph_includes_orderbook_state_in_collect_sources(self):
        """El grafo debe incluir orderbook_state en sources del nodo collect_state."""
        config = {}
        out = compile_liquidity_near_end(config)
        graph = out["decision_graph"]
        collect_node = graph["nodes"].get("collect_state")
        assert collect_node is not None
        sources = collect_node["config"].get("sources", [])
        assert "orderbook_state" in sources

    def test_graph_has_price_conditions_with_orderbook_state(self):
        """El grafo debe tener condiciones de precio que usan orderbook_state."""
        config = {"price_min": 0.95, "price_max": 0.98}
        out = compile_liquidity_near_end(config)
        graph = out["decision_graph"]
        check_price = graph["nodes"].get("check_price_range")
        assert check_price is not None
        conditions = check_price["config"].get("conditions", [])
        fields = [c["field"] for c in conditions]
        assert "orderbook_state.best_ask_price" in fields
        assert "orderbook_state.staleness_ms" in fields
        assert "orderbook_state.spread_bps" in fields
        assert "orderbook_state.depth_usdc_at_50bps" in fields
        assert "orderbook_state.impact_bps_for_usdc_1000" in fields

    def test_graph_respects_orderbook_config_defaults(self):
        """Los defaults de orderbook (staleness, spread, depth, impact) se aplican."""
        config = {}
        out = compile_liquidity_near_end(config)
        graph = out["decision_graph"]
        check_price = graph["nodes"].get("check_price_range")
        conditions = {c["field"]: c["value"] for c in check_price["config"]["conditions"]}
        assert conditions.get("orderbook_state.staleness_ms") == 2000
        assert conditions.get("orderbook_state.spread_bps") == 200
        assert conditions.get("orderbook_state.depth_usdc_at_50bps") == 1000.0
        assert conditions.get("orderbook_state.impact_bps_for_usdc_1000") == 200
