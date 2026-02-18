"""Tests para process_telegram_message (texto → parser; imagen → Vision fallback)."""
import pytest

from app.core.tipster.message import process_telegram_message


class TestProcessTelegramMessage:
    def test_text_only_uses_parser(self):
        raw = "Real Madrid vs Barcelona, Over 2.5 @ 1.85, 2u"
        out = process_telegram_message(raw_text=raw)
        assert out.get("error") is None
        assert "partido" in out
        assert "Real Madrid" in (out.get("partido") or "")
        assert out.get("cuota") == 1.85
        assert out.get("stake") == 2.0

    def test_empty_text_returns_no_tip(self):
        out = process_telegram_message(raw_text="")
        assert out.get("error") == "no_tip" or "partido" not in out or not out.get("partido")

    def test_image_without_openai_fallback_to_text(self):
        # Sin API key, Vision devuelve error; si hay texto largo, se usa parser como fallback
        raw = "Atletico vs Sevilla, 1 @ 2.10, 1u"
        out = process_telegram_message(raw_text=raw, image_bytes=b"fake", caption=None)
        assert out.get("error") is None
        assert "partido" in out
        assert out.get("cuota") == 2.10
        assert out.get("stake") == 1.0

    def test_text_only_short_no_tip(self):
        out = process_telegram_message(raw_text="hi")
        assert out.get("error") == "no_tip" or not out.get("partido")
