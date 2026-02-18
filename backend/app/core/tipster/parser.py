"""
Parser de tips en texto: regex y heurísticas para extraer partido, selección, stake, odds.
"""
import re
from typing import Any, Dict, Optional


# Patrones comunes: "Equipo1 vs Equipo2", "Equipo1 - Equipo2", "Equipo1 v Equipo2"
# Segundo grupo hasta coma, punto y coma o fin para no incluir " 1 @1.85" en el visitante
PARTIDO_PATTERNS = [
    re.compile(r"(.+?)\s+vs\.?\s+([^,;]+?)(?:\s*[,;]|\s*$)", re.I),
    re.compile(r"(.+?)\s+-\s+([^,;]+?)(?:\s*[,;]|\s*$)", re.I),
    re.compile(r"(.+?)\s+v\s+([^,;]+?)(?:\s*[,;]|\s*$)", re.I),
]

# Cuota: @1.85, 1.85, odds 1.85, cuota 1.85
ODDS_PATTERNS = [
    re.compile(r"@\s*(\d+[.,]\d+)", re.I),
    re.compile(r"odds?\s*[:=]?\s*(\d+[.,]\d+)", re.I),
    re.compile(r"cuota\s*[:=]?\s*(\d+[.,]\d+)", re.I),
    re.compile(r"\b(\d+[.,]\d{2})\s*(?:€|eur|usd)?\s*(?=.*(?:stake|u\.|unidades))", re.I),
]

# Stake: stake 3, 3u, 3 unidades, 3€
STAKE_PATTERNS = [
    re.compile(r"stake\s*[:=]?\s*(\d+[.,]?\d*)", re.I),
    re.compile(r"(\d+[.,]?\d*)\s*u\.?\s*(?:nit|nits|unidades)?", re.I),
    re.compile(r"(\d+[.,]?\d*)\s*unidades", re.I),
    re.compile(r"(\d+[.,]?\d*)\s*(?:€|eur|usd)\b", re.I),
]

# Selección: 1, X, 2, Over 2.5, Under 2.5, BTTS Yes, AH -1.5, etc.
SELECTION_PATTERNS = [
    (re.compile(r"\bover\s*(\d+[.,]?\d*)\b", re.I), "Over {}"),
    (re.compile(r"\bunder\s*(\d+[.,]?\d*)\b", re.I), "Under {}"),
    (re.compile(r"\b(?:btts|gg)\s*yes\b", re.I), "BTTS Yes"),
    (re.compile(r"\b(?:btts|gg)\s*no\b", re.I), "BTTS No"),
    (re.compile(r"\bah\s*([+-]?\d+[.,]?\d*)\s*(?:local|home|1)\b", re.I), "AH {} Local"),
    (re.compile(r"\bah\s*([+-]?\d+[.,]?\d*)\s*(?:visitante|away|2)\b", re.I), "AH {} Away"),
    (re.compile(r"\b(1|2)\s*(?:@|\s)", re.I), "{}"),  # 1 o 2 como selección
    (re.compile(r"\b(?:local|home)\b", re.I), "1"),
    (re.compile(r"\b(?:visitante|away)\b", re.I), "2"),
    (re.compile(r"\b(empate|draw|x)\b", re.I), "X"),
]


def _first_match(patterns: list, text: str) -> Optional[str]:
    """Devuelve la primera captura que coincida (o el grupo 1 si es tupla (regex, fmt))."""
    for item in patterns:
        if isinstance(item, tuple):
            m = item[0].search(text)
            if m:
                if item[1].count("{}") == 1:
                    return item[1].format(m.group(1).replace(",", "."))
                return item[1]
        else:
            m = item.search(text)
            if m:
                return m.group(1).replace(",", ".")
    return None


def parse_tip_text(raw_text: str) -> Dict[str, Any]:
    """
    Parsea un mensaje de texto y extrae partido, selección, stake y cuota si aparecen.

    Returns:
        dict con keys: partido, home, away, seleccion, cuota, stake, tipo_apuesta, confianza, error.
        confianza en 0-1 (heurística según cuántos campos se encontraron).
        error = "no_es_tip" si no se detecta ningún indicio de tip.
    """
    text = (raw_text or "").strip()
    result = {
        "partido": None,
        "home": None,
        "away": None,
        "seleccion": None,
        "cuota": None,
        "stake": None,
        "tipo_apuesta": None,
        "confianza": 0.0,
        "error": None,
    }
    if not text or len(text) < 5:
        result["error"] = "no_es_tip"
        return result
    # Partido
    for pat in PARTIDO_PATTERNS:
        m = pat.search(text)
        if m:
            result["home"] = m.group(1).strip()
            result["away"] = m.group(2).strip()
            result["partido"] = f"{result['home']} vs {result['away']}"
            break
    # Cuota
    odds_str = _first_match(ODDS_PATTERNS, text)
    if odds_str:
        try:
            result["cuota"] = float(odds_str)
        except (ValueError, TypeError):
            pass
    # Stake
    stake_str = _first_match(STAKE_PATTERNS, text)
    if stake_str:
        try:
            result["stake"] = float(stake_str)
        except (ValueError, TypeError):
            pass
    # Selección
    for pat, fmt in SELECTION_PATTERNS:
        m = pat.search(text)
        if m:
            if "{}" in fmt:
                result["seleccion"] = fmt.format(m.group(1).replace(",", "."))
            else:
                result["seleccion"] = fmt
            if "Over" in (result["seleccion"] or "") or "Under" in (result["seleccion"] or ""):
                result["tipo_apuesta"] = "TOTAL_POINTS"
            elif result["seleccion"] in ("1", "X", "2"):
                result["tipo_apuesta"] = "MONEYLINE"
            elif result["seleccion"] and "AH" in result["seleccion"]:
                result["tipo_apuesta"] = "SPREAD"
            elif "BTTS" in (result["seleccion"] or ""):
                result["tipo_apuesta"] = "BTTS"
            break
    # Confianza heurística
    filled = sum(1 for k in ("partido", "seleccion", "cuota", "stake") if result.get(k))
    if filled == 0:
        result["error"] = "no_es_tip"
        return result
    result["confianza"] = round(0.3 + 0.15 * filled, 2)
    result["confianza"] = min(1.0, result["confianza"])
    return result
