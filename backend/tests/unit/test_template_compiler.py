"""
Tests unitarios para el Template Compiler (Near-Resolution y Telegram Tipster PS3838).
"""
import pytest

from app.core.strategy_engine.template_compiler import (
    compile_liquidity_near_end,
    compile_telegram_tipster_ps3838,
    compile_strategy,
)


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


class TestCompileTelegramTipsterPs3838:
    """Tests para compile_telegram_tipster_ps3838."""

    def test_returns_decision_execution_support_and_risk_config(self):
        """El compiler devuelve decision_graph, execution_graph, support_graphs y risk_config."""
        config = {
            "ps3838_source_id": "uuid-ps3838",
            "telegram_source_id": "uuid-telegram",
            "max_stake_per_tip": 80,
            "max_daily_stake": 400,
        }
        out = compile_telegram_tipster_ps3838(config)
        assert "decision_graph" in out
        assert "execution_graph" in out
        assert "support_graphs" in out
        assert "risk_config" in out

    def test_replaces_ps3838_and_telegram_source_id_in_graphs(self):
        """Los placeholders {{ps3838_source_id}} y {{telegram_source_id}} se reemplazan."""
        config = {
            "ps3838_source_id": "abc-ps3838",
            "telegram_source_id": "xyz-telegram",
            "max_stake_per_tip": 50,
            "max_daily_stake": 300,
        }
        out = compile_telegram_tipster_ps3838(config)
        eg = out["execution_graph"]
        # place_bet_ps3838 debe tener source_id reemplazado
        place_bet = eg["nodes"].get("place_bet", {})
        assert place_bet.get("config", {}).get("source_id") == "abc-ps3838"
        support = out["support_graphs"]
        telegram_graph = next((g for g in support if g.get("name") == "telegram_listener"), None)
        assert telegram_graph is not None
        listen_node = telegram_graph.get("nodes", {}).get("listen", {})
        assert listen_node.get("config", {}).get("source_id") == "xyz-telegram"

    def test_risk_config_uses_form_values(self):
        """risk_config usa max_stake_per_tip y max_daily_stake del formulario."""
        config = {
            "ps3838_source_id": "x",
            "telegram_source_id": "y",
            "max_stake_per_tip": 100,
            "max_daily_stake": 500,
        }
        out = compile_telegram_tipster_ps3838(config)
        assert out["risk_config"]["max_stake_per_tip"] == 100
        assert out["risk_config"]["max_daily_stake"] == 500

    def test_compile_strategy_resolves_telegram_tipster_template(self):
        """compile_strategy(template_id, config) funciona para telegram_tipster_ps3838."""
        config = {
            "ps3838_source_id": "sid-1",
            "telegram_source_id": "sid-2",
            "max_stake_per_tip": 30,
            "max_daily_stake": 200,
        }
        out = compile_strategy("telegram_tipster_ps3838", config)
        assert out["execution_graph"]["nodes"]["place_bet"]["config"]["source_id"] == "sid-1"
        assert out["risk_config"]["max_stake_per_tip"] == 30

    def test_chat_filters_and_per_channel_limits_in_risk_config(self):
        """risk_config incluye chat_filters, per_channel_limits, tipster y sport filters."""
        config = {
            "ps3838_source_id": "x",
            "telegram_source_id": "y",
            "chat_filters": {"-100": {"include_regex": r"#pick", "exclude_regex": "free"}},
            "per_channel_limits": {"-100": {"max_tips_per_day": 5}},
            "tipster_whitelist_regex": "tipster_a, tipster_b",
            "tipster_blacklist_regex": "spam",
            "sport_filters": "football, basketball",
        }
        out = compile_telegram_tipster_ps3838(config)
        rc = out["risk_config"]
        assert rc["chat_filters"] == {"-100": {"include_regex": "#pick", "exclude_regex": "free"}}
        assert rc["per_channel_limits"] == {"-100": {"max_tips_per_day": 5}}
        assert "tipster_a" in rc["tipster_whitelist_regex"]
        assert "tipster_b" in rc["tipster_whitelist_regex"]
        assert "spam" in rc["tipster_blacklist_regex"]
        assert "football" in rc["sport_filters"]
        assert "basketball" in rc["sport_filters"]

    def test_invalid_regex_raises_value_error(self):
        """Regex inválidos en chat_filters o tipster levantan ValueError."""
        with pytest.raises(ValueError, match="regex inválido"):
            compile_telegram_tipster_ps3838({
                "ps3838_source_id": "x",
                "telegram_source_id": "y",
                "chat_filters": {"-100": {"include_regex": "[invalid"}},
            })
        with pytest.raises(ValueError, match="regex inválido"):
            compile_telegram_tipster_ps3838({
                "ps3838_source_id": "x",
                "telegram_source_id": "y",
                "tipster_blacklist_regex": "[unclosed",
            })
