"""
Procesamiento de un mensaje Telegram: texto → parser; imagen → Vision.
Opcionalmente crea TipIntent (PENDING).
"""
import logging
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.tipster.parser import parse_tip_text
from app.core.tipster.vision import openai_extract_tip

logger = logging.getLogger(__name__)


def process_telegram_message(
    raw_text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    caption: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Procesa un mensaje de Telegram (solo texto, o imagen + caption).
    - Si hay solo texto: usa parse_tip_text.
    - Si hay imagen (con o sin caption): usa openai_extract_tip; si no hay caption útil y hay texto, usa también el texto.
    Returns: dict parseado (partido, seleccion, cuota, stake, confianza, error).
    """
    if image_bytes:
        parsed = openai_extract_tip(image_bytes, caption=caption or raw_text)
        if parsed.get("error") and raw_text and len((raw_text or "").strip()) > 10:
            text_parsed = parse_tip_text(raw_text)
            if not text_parsed.get("error"):
                return text_parsed
        return parsed
    return parse_tip_text(raw_text or "")
