"""
Extracción de tips desde imágenes con OpenAI Vision (gpt-4o / gpt-4o-mini).
"""
import base64
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

VISION_PROMPT = """Eres un experto en apuestas deportivas y extracción de tips. Analiza esta imagen (captura de ticket o tipster) y el caption proporcionado (si existe). Extrae la información clave en formato JSON estricto:

{
  "partido": "Equipo Local vs Equipo Visitante" o null,
  "fecha_hora": "2026-02-20 20:00" o null (formato ISO si posible),
  "seleccion": "Over 2.5" | "1" | "X" | "2" | "AH -1.5 Local" | "BTTS Yes" | etc.,
  "cuota": 1.92 | null,
  "stake": 4.5 | null (unidades o valor absoluto),
  "tipo_apuesta": "TOTAL_POINTS" | "MONEYLINE" | "SPREAD" | "BTTS" | "THREE_WAY" | etc.,
  "confianza": 0.0-1.0 (tu estimación de que es un tip válido y bien extraído),
  "error": null | "no_es_tip" | "imagen_no_legible"
}

Reglas:
- Usa el caption como contexto prioritario si está presente.
- Si no hay tip claro o la imagen no contiene apuesta, responde solo con {"error": "no_es_tip"}.
- Responde ÚNICAMENTE con JSON válido, sin texto adicional."""


def openai_extract_tip(
    image_bytes: bytes,
    caption: Optional[str] = None,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extrae información de tip desde una imagen usando OpenAI Vision.

    Args:
        image_bytes: bytes de la imagen (JPEG/PNG).
        caption: texto opcional (caption del mensaje) para contexto.
        model: modelo a usar (gpt-4o, gpt-4o-mini).
        api_key: clave API OpenAI (si no se pasa, se usa OPENAI_API_KEY env).

    Returns:
        dict con partido, seleccion, cuota, stake, tipo_apuesta, confianza, error.
        Si la API falla o no hay key, devuelve {"error": "imagen_no_legible"}.
    """
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; cannot extract tip from image")
        return {"error": "imagen_no_legible", "confianza": 0.0}
    key = api_key or __import__("os").environ.get("OPENAI_API_KEY")
    if not key:
        logger.warning("OPENAI_API_KEY not set; cannot call Vision API")
        return {"error": "imagen_no_legible", "confianza": 0.0}
    prompt = VISION_PROMPT
    if caption:
        prompt = f"Caption del mensaje: \"{caption}\"\n\n{prompt}"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    mime = "image/jpeg" if (len(image_bytes) >= 2 and image_bytes[:2] == b"\xff\xd8") else "image/png"
    url = f"data:{mime};base64,{b64}"
    client = OpenAI(api_key=key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": url}}]},
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.exception("OpenAI Vision API error: %s", e)
        return {"error": "imagen_no_legible", "confianza": 0.0}
    choice = resp.choices[0] if resp.choices else None
    if not choice or not getattr(choice, "message", None):
        return {"error": "imagen_no_legible", "confianza": 0.0}
    text = choice.message.content
    if not text:
        return {"error": "imagen_no_legible", "confianza": 0.0}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON: %s", text[:200])
        return {"error": "imagen_no_legible", "confianza": 0.0}
    if not isinstance(data, dict):
        return {"error": "no_es_tip", "confianza": 0.0}
    # Normalizar keys al mismo formato que parse_tip_text
    out = {
        "partido": data.get("partido"),
        "seleccion": data.get("seleccion"),
        "cuota": data.get("cuota"),
        "stake": data.get("stake"),
        "tipo_apuesta": data.get("tipo_apuesta"),
        "confianza": float(data.get("confianza", 0.5)),
        "error": data.get("error"),
    }
    if out.get("partido") and " vs " in str(out["partido"]):
        parts = str(out["partido"]).split(" vs ", 1)
        out["home"] = parts[0].strip() if len(parts) > 0 else None
        out["away"] = parts[1].strip() if len(parts) > 1 else None
    return out
