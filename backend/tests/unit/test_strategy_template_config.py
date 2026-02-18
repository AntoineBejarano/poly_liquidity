"""
Tests unitarios para strategy_template_config.
Asegura que todas las plantillas usadas en la UI (incl. Telegram Tipster) estén registradas.
"""
import pytest

from app.models.strategy_template_config import (
    get_template_config,
    list_template_configs,
    TEMPLATE_CONFIGS,
)


class TestTemplateConfigRegistry:
    """La plantilla telegram_tipster_ps3838 debe estar registrada para la API y la UI."""

    def test_telegram_tipster_ps3838_is_registered(self):
        """GET /strategy-templates/telegram_tipster_ps3838 debe encontrar la plantilla."""
        config = get_template_config("telegram_tipster_ps3838")
        assert config is not None
        assert config.template_id == "telegram_tipster_ps3838"
        assert "Telegram" in config.name and "PS3838" in config.name
        assert config.fields
        assert config.compiler == "compile_telegram_tipster_ps3838"

    def test_list_includes_telegram_tipster(self):
        """GET /strategy-templates debe devolver la plantilla en la lista."""
        listed = list_template_configs()
        ids = [t["id"] for t in listed]
        assert "telegram_tipster_ps3838" in ids

    def test_template_configs_has_expected_keys(self):
        """TEMPLATE_CONFIGS incluye las tres plantillas usadas en la app."""
        expected = {"liquidity_near_end", "surebet_polymarket_pinnacle", "telegram_tipster_ps3838"}
        assert set(TEMPLATE_CONFIGS.keys()) >= expected
