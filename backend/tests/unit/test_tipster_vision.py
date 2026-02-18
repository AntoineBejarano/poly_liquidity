"""
Tests unitarios para openai_extract_tip (Vision). OpenAI se mockea (funciona sin tener openai instalado).
"""
import sys
import pytest
from unittest.mock import patch, MagicMock

from app.core.tipster.vision import openai_extract_tip, VISION_PROMPT


def _make_fake_openai_module(create_return_value=None):
    """Crea un módulo openai falso para inyectar en sys.modules."""
    fake = MagicMock()
    fake.OpenAI = MagicMock()
    if create_return_value is not None:
        fake.OpenAI.return_value.chat.completions.create.return_value = create_return_value
    return fake


class TestOpenaiExtractTip:
    """Tests para openai_extract_tip."""

    def test_returns_error_when_no_api_key(self):
        # Sin api_key y sin OPENAI_API_KEY en env → no llama a OpenAI
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            out = openai_extract_tip(b"\xff\xd8\xfffake_jpeg", api_key=None)
        assert "error" in out
        assert out.get("error") == "imagen_no_legible"

    def test_returns_parsed_json_when_mocked(self):
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = '{"partido": "A vs B", "seleccion": "Over 2.5", "cuota": 1.9, "confianza": 0.85, "error": null}'
        fake_openai = _make_fake_openai_module(fake_response)
        with patch.dict(sys.modules, {"openai": fake_openai}):
            out = openai_extract_tip(b"\xff\xd8\xfffake", api_key="sk-test")
        assert out.get("partido") == "A vs B"
        assert out.get("seleccion") == "Over 2.5"
        assert out.get("cuota") == 1.9
        assert out.get("confianza") == 0.85

    def test_includes_caption_in_prompt_when_provided(self):
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = '{"error": "no_es_tip"}'
        fake_openai = _make_fake_openai_module(fake_response)
        with patch.dict(sys.modules, {"openai": fake_openai}):
            openai_extract_tip(b"\xff\xd8\xff", caption="Over 2.5 @1.85", api_key="sk-test")
            call = fake_openai.OpenAI.return_value.chat.completions.create.call_args
            content = call[1]["messages"][0]["content"]
            text_part = next(c for c in content if c.get("type") == "text")
            assert "Over 2.5" in text_part["text"]
            assert "Caption" in text_part["text"]

    def test_uses_response_format_json_object(self):
        fake_response = MagicMock()
        fake_response.choices = [MagicMock()]
        fake_response.choices[0].message.content = '{"error": null}'
        fake_openai = _make_fake_openai_module(fake_response)
        with patch.dict(sys.modules, {"openai": fake_openai}):
            openai_extract_tip(b"\x89PNG", api_key="sk-test")
            call = fake_openai.OpenAI.return_value.chat.completions.create.call_args
            assert call[1].get("response_format") == {"type": "json_object"}
