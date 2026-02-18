"""
Match resolution: tip parseado (partido, selección) → evento y línea PS3838.

Recibe tip con partido (equipos) y opcionalmente selección/odds.
Compara con fixtures y odds de PS3838; devuelve eventId, lineId, odds y confidence.
"""
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _normalize_team_name(name: str) -> str:
    """Normaliza nombre de equipo para comparación."""
    if not name or not isinstance(name, str):
        return ""
    s = name.lower().strip()
    s = re.sub(r"\s+", " ", s)
    # Quitar acentos básicos (expandir si hace falta)
    for old, new in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        s = s.replace(old, new)
    return s


def _similarity(a: str, b: str) -> float:
    """Similitud entre 0 y 1 (SequenceMatcher)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize_team_name(a), _normalize_team_name(b)).ratio()


def resolve_tip_to_ps3838(
    parsed_tip: Dict[str, Any],
    fixtures: List[Dict[str, Any]],
    odds: List[Dict[str, Any]],
    min_confidence: float = 0.5,
) -> Dict[str, Any]:
    """
    Resuelve un tip parseado al evento y línea de PS3838.

    parsed_tip: dict con al menos "partido" (str "Equipo1 vs Equipo2") o "home", "away".
    fixtures: lista de eventos de Get Fixtures (cada uno con id, home/away, etc.).
    odds: lista de Get Odds (para obtener lineId y cuotas).
    min_confidence: umbral mínimo de confianza (0-1).

    Returns:
        {
            "ps3838_event_id": int | None,
            "ps3838_league_id": int | None,
            "period_number": int | None,
            "line_id": int | None,
            "ps3838_odds": float | None,
            "confidence": float,
            "matched": bool,
        }
    """
    result = {
        "ps3838_event_id": None,
        "ps3838_league_id": None,
        "period_number": None,
        "line_id": None,
        "ps3838_odds": None,
        "confidence": 0.0,
        "matched": False,
    }
    partido = parsed_tip.get("partido") or ""
    home_tip = parsed_tip.get("home") or ""
    away_tip = parsed_tip.get("away") or ""
    if partido and not (home_tip or away_tip):
        parts = re.split(r"\s+vs\.?\s+|\s+-\s+|\s+v\s+", partido, maxsplit=1, flags=re.I)
        if len(parts) >= 2:
            home_tip, away_tip = parts[0].strip(), parts[1].strip()
    if not home_tip and not away_tip:
        return result
    best_event: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for event in fixtures:
        eid = event.get("id")
        # Estructura típica: event con homeTeamId/awayTeamId o home/away como nombres
        home = event.get("homeTeamName") or event.get("home") or event.get("homeTeam") or ""
        away = event.get("awayTeamName") or event.get("away") or event.get("awayTeam") or ""
        if not home and not away:
            continue
        sh = _similarity(home_tip, home) if home else 0
        sa = _similarity(away_tip, away) if away else 0
        score = (sh + sa) / 2.0 if (home and away) else max(sh, sa)
        if score > best_score and score >= min_confidence:
            best_score = score
            best_event = event
    if not best_event:
        return result
    result["ps3838_event_id"] = best_event.get("id")
    result["ps3838_league_id"] = best_event.get("leagueId") or best_event.get("league_id")
    result["period_number"] = best_event.get("periodNumber") or best_event.get("period_number") or 0
    result["confidence"] = round(best_score, 4)
    result["matched"] = True
    # Intentar obtener lineId y odds del primer periodo si hay odds
    event_id = result["ps3838_event_id"]
    for o in odds:
        if o.get("eventId") == event_id or o.get("event_id") == event_id:
            result["line_id"] = o.get("lineId") or o.get("line_id")
            result["ps3838_odds"] = o.get("odds") or o.get("price")
            break
    return result
