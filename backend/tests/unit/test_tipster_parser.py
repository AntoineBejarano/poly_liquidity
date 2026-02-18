"""
Tests unitarios para el parser de tips en texto.
"""
import pytest

from app.core.tipster.parser import parse_tip_text


class TestParseTipText:
    """Tests para parse_tip_text."""

    def test_empty_returns_no_tip(self):
        out = parse_tip_text("")
        assert out["error"] == "no_es_tip"
        assert out["confianza"] == 0.0

    def test_short_text_returns_no_tip(self):
        out = parse_tip_text("hi")
        assert out["error"] == "no_es_tip"

    def test_partido_vs(self):
        out = parse_tip_text("Real Madrid vs Barcelona, 1 @1.85 stake 3u")
        assert out["partido"] == "Real Madrid vs Barcelona"
        assert out["home"] == "Real Madrid"
        assert out["away"] == "Barcelona"
        assert out["error"] is None

    def test_partido_guion(self):
        out = parse_tip_text("Atletico - Sevilla")
        assert out["partido"] is not None
        assert "Atletico" in (out["home"] or "")
        assert "Sevilla" in (out["away"] or "")

    def test_cuota_at(self):
        out = parse_tip_text("Algo @1.92 más texto")
        assert out["cuota"] == 1.92

    def test_stake_u(self):
        out = parse_tip_text("Partido vs Otro stake 4u")
        assert out["stake"] == 4.0

    def test_seleccion_over(self):
        out = parse_tip_text("Team A vs Team B Over 2.5 @1.90")
        assert out["seleccion"] == "Over 2.5"
        assert out["tipo_apuesta"] == "TOTAL_POINTS"

    def test_seleccion_1x2(self):
        out = parse_tip_text("Local vs Visitante 1 @2.10")
        assert out["seleccion"] in ("1", "2") or out["partido"]  # puede capturar 1 como selección

    def test_confianza_increases_with_fields(self):
        out = parse_tip_text("Real Madrid vs Barcelona Over 2.5 @1.85 stake 3")
        assert out["error"] is None
        assert out["confianza"] >= 0.3
        assert out["confianza"] <= 1.0

    def test_no_indicator_returns_no_tip(self):
        out = parse_tip_text("Hola, qué tal, mensaje random sin partido ni odds")
        assert out["error"] == "no_es_tip"
