"""
Tipster: parser de texto y extracción de tips desde imágenes (OpenAI Vision).
"""
from app.core.tipster.parser import parse_tip_text
from app.core.tipster.vision import openai_extract_tip

__all__ = ["parse_tip_text", "openai_extract_tip"]
