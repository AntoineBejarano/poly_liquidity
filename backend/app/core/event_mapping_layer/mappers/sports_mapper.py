"""
Sports Mapper - mapea mercados deportivos a eventos reales (ESPN).
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from app.core.scanner.models import CandidateMarket
from app.core.event_mapping_layer.models import EventDescriptor, EventType
from app.core.event_mapping_layer.mappers.base_mapper import BaseMapper


class SportsMapper(BaseMapper):
    """
    Mapper para eventos deportivos.
    
    MVP: Usa heurísticas y diccionarios de equipos para mapear a eventos de ESPN.
    """
    
    # Diccionario de alias a nombres canónicos de equipos NBA
    NBA_TEAM_ALIASES = {
        "LAL": "Los Angeles Lakers",
        "Lakers": "Los Angeles Lakers",
        "GSW": "Golden State Warriors",
        "Warriors": "Golden State Warriors",
        "BOS": "Boston Celtics",
        "Celtics": "Boston Celtics",
        "MIA": "Miami Heat",
        "Heat": "Miami Heat",
        "MIL": "Milwaukee Bucks",
        "Bucks": "Milwaukee Bucks",
        "PHI": "Philadelphia 76ers",
        "76ers": "Philadelphia 76ers",
        "NYK": "New York Knicks",
        "Knicks": "New York Knicks",
        "BKN": "Brooklyn Nets",
        "Nets": "Brooklyn Nets",
        "CHI": "Chicago Bulls",
        "Bulls": "Chicago Bulls",
        "DAL": "Dallas Mavericks",
        "Mavericks": "Dallas Mavericks",
        "DEN": "Denver Nuggets",
        "Nuggets": "Denver Nuggets",
        "HOU": "Houston Rockets",
        "Rockets": "Houston Rockets",
        "LAC": "LA Clippers",
        "Clippers": "LA Clippers",
        "MEM": "Memphis Grizzlies",
        "Grizzlies": "Memphis Grizzlies",
        "MIN": "Minnesota Timberwolves",
        "Timberwolves": "Minnesota Timberwolves",
        "NOP": "New Orleans Pelicans",
        "Pelicans": "New Orleans Pelicans",
        "OKC": "Oklahoma City Thunder",
        "Thunder": "Oklahoma City Thunder",
        "ORL": "Orlando Magic",
        "Magic": "Orlando Magic",
        "PHX": "Phoenix Suns",
        "Suns": "Phoenix Suns",
        "POR": "Portland Trail Blazers",
        "Trail Blazers": "Portland Trail Blazers",
        "SAC": "Sacramento Kings",
        "Kings": "Sacramento Kings",
        "SAS": "San Antonio Spurs",
        "Spurs": "San Antonio Spurs",
        "TOR": "Toronto Raptors",
        "Raptors": "Toronto Raptors",
        "UTA": "Utah Jazz",
        "Jazz": "Utah Jazz",
        "WAS": "Washington Wizards",
        "Wizards": "Washington Wizards",
    }
    
    # Patrones para detectar equipos
    PATTERN_VS = re.compile(r"(\w+(?:\s+\w+)*)\s+vs\.?\s+(\w+(?:\s+\w+)*)", re.IGNORECASE)
    PATTERN_AT = re.compile(r"(\w+(?:\s+\w+)*)\s+@\s+(\w+(?:\s+\w+)*)", re.IGNORECASE)
    
    def __init__(self):
        """Inicializa el Sports Mapper."""
        self._cache: Dict[str, EventDescriptor] = {}  # Cache simple por market_id
    
    async def map(self, candidate_market: CandidateMarket, trace_id: str) -> EventDescriptor:
        """
        Mapea un mercado deportivo a un evento real.
        
        Args:
            candidate_market: Mercado candidato del Scanner
            trace_id: ID de trazabilidad
        
        Returns:
            EventDescriptor con el resultado del mapping
        """
        # Verificar cache
        cache_key = candidate_market.polymarket_id
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Crear copia con nuevo trace_id
            from copy import deepcopy
            cached_copy = deepcopy(cached)
            cached_copy.trace_id = UUID(trace_id) if isinstance(trace_id, str) else trace_id
            return cached_copy
        
        # Paso 1: Extraer equipos
        teams = self._extract_teams(candidate_market)
        
        if len(teams) < 2:
            return EventDescriptor(
                market_id=candidate_market.polymarket_id,
                mapped=False,
                event_type=EventType.SPORTS,
                mapping_confidence=0.0,
                reason="insufficient_teams_detected",
                trace_id=UUID(trace_id) if isinstance(trace_id, str) else trace_id,
                metadata={}
            )
        
        # Paso 2: Determinar deporte y liga
        sport, league = self._determine_sport_and_league(teams, candidate_market)
        
        if not sport or not league:
            return EventDescriptor(
                market_id=candidate_market.polymarket_id,
                mapped=False,
                event_type=EventType.SPORTS,
                mapping_confidence=0.0,
                reason="unknown_sport_or_league",
                trace_id=UUID(trace_id) if isinstance(trace_id, str) else trace_id,
                metadata={"teams": teams}
            )
        
        # Paso 3: Buscar eventos en calendario deportivo (simulado para MVP)
        # En producción, esto llamaría a ESPN API
        espn_events = await self._search_espn_events(sport, league, teams, candidate_market)
        
        if not espn_events:
            return EventDescriptor(
                market_id=candidate_market.polymarket_id,
                mapped=False,
                event_type=EventType.SPORTS,
                mapping_confidence=0.0,
                reason="no_events_found",
                trace_id=UUID(trace_id) if isinstance(trace_id, str) else trace_id,
                metadata={
                    "teams": teams,
                    "sport": sport,
                    "league": league
                }
            )
        
        # Paso 4: Matching por equipos + fecha
        best_match = self._match_event(teams, candidate_market, espn_events)
        
        if not best_match:
            return EventDescriptor(
                market_id=candidate_market.polymarket_id,
                mapped=False,
                event_type=EventType.SPORTS,
                mapping_confidence=0.0,
                reason="no_matching_event",
                trace_id=UUID(trace_id) if isinstance(trace_id, str) else trace_id,
                metadata={
                    "teams": teams,
                    "sport": sport,
                    "league": league,
                    "candidates": len(espn_events)
                }
            )
        
        # Paso 5: Calcular confianza
        entity_score = self._calculate_team_match(teams, best_match.get("teams", []))
        date_score = self._calculate_date_match(
            candidate_market.event_start_time or candidate_market.close_time,
            best_match.get("starts_at")
        )
        source_score = 1.0  # ESPN es fuente confiable
        
        confidence = self.calculate_confidence(entity_score, date_score, source_score)
        
        # Paso 6: Generar EventDescriptor
        canonical_event_id = f"sports:{league}:{best_match.get('espn_event_id', 'unknown')}"
        
        descriptor = EventDescriptor(
            market_id=candidate_market.polymarket_id,
            mapped=confidence >= 0.7,  # Solo mapear si confianza >= 0.7
            event_type=EventType.SPORTS,
            mapping_confidence=confidence,
            canonical_event_id=canonical_event_id if confidence >= 0.7 else None,
            sources=["espn"] if confidence >= 0.7 else [],
            metadata={
                "sport": sport,
                "league": league,
                "espn_event_id": best_match.get("espn_event_id"),
                "teams": best_match.get("teams", teams),
                "starts_at": best_match.get("starts_at").isoformat() if best_match.get("starts_at") else None,
                "venue": best_match.get("venue")
            },
            reason=None if confidence >= 0.7 else f"low_confidence_{confidence:.2f}",
            trace_id=UUID(trace_id) if isinstance(trace_id, str) else trace_id
        )
        
        # Guardar en cache
        self._cache[cache_key] = descriptor
        
        return descriptor
    
    def calculate_confidence(
        self,
        entity_match_score: float,
        date_match_score: float,
        source_reliability_score: float
    ) -> float:
        """
        Calcula la confianza del mapping.
        
        Args:
            entity_match_score: Coincidencia de entidades (0.0 - 1.0)
            date_match_score: Coincidencia de fechas (0.0 - 1.0)
            source_reliability_score: Confiabilidad de la fuente (0.0 - 1.0)
        
        Returns:
            Confianza total (0.0 - 1.0)
        """
        return (
            0.6 * entity_match_score +
            0.25 * date_match_score +
            0.15 * source_reliability_score
        )
    
    def _extract_teams(self, candidate_market: CandidateMarket) -> List[str]:
        """Extrae equipos del mercado."""
        teams = []
        
        # Usar metadata del evento si está disponible
        if candidate_market.event_metadata and candidate_market.event_metadata.detected_teams:
            teams = candidate_market.event_metadata.detected_teams.copy()
        else:
            # Extraer desde pregunta
            question = candidate_market.question
            
            # Buscar patrón "vs"
            match = self.PATTERN_VS.search(question)
            if match:
                teams = [match.group(1).strip(), match.group(2).strip()]
            
            # Buscar patrón "@"
            if not teams:
                match = self.PATTERN_AT.search(question)
                if match:
                    teams = [match.group(1).strip(), match.group(2).strip()]
        
        # Normalizar usando diccionario de alias
        normalized_teams = []
        for team in teams:
            normalized = self.NBA_TEAM_ALIASES.get(team, team)
            if normalized not in normalized_teams:
                normalized_teams.append(normalized)
        
        return normalized_teams
    
    def _determine_sport_and_league(self, teams: List[str], candidate_market: CandidateMarket) -> Tuple[Optional[str], Optional[str]]:
        """Determina deporte y liga a partir de equipos y categoría."""
        # Verificar subcategoría
        if candidate_market.subcategory:
            subcat_lower = candidate_market.subcategory.lower()
            if "basketball" in subcat_lower or "nba" in subcat_lower:
                return ("basketball", "nba")
            elif "football" in subcat_lower or "nfl" in subcat_lower:
                return ("football", "nfl")
            elif "soccer" in subcat_lower:
                return ("soccer", "mls")
        
        # Verificar equipos conocidos (NBA por ahora)
        nba_teams = set(self.NBA_TEAM_ALIASES.values())
        if any(team in nba_teams for team in teams):
            return ("basketball", "nba")
        
        return (None, None)
    
    async def _search_espn_events(
        self,
        sport: str,
        league: str,
        teams: List[str],
        candidate_market: CandidateMarket
    ) -> List[Dict[str, Any]]:
        """
        Busca eventos en ESPN (simulado para MVP).
        
        En producción, esto haría llamadas reales a ESPN API.
        """
        # TODO: Implementar llamadas reales a ESPN API
        # Por ahora, retornar lista vacía (simula que no se encontraron eventos)
        # En producción, esto buscaría eventos en un rango de fechas
        
        # Simulación: si tenemos equipos NBA conocidos, crear evento simulado
        if league == "nba" and len(teams) >= 2:
            # Crear evento simulado
            event_date = candidate_market.event_start_time or candidate_market.close_time or datetime.utcnow()
            
            return [{
                "espn_event_id": f"sim_{hash(''.join(teams)) % 1000000}",
                "teams": teams,
                "starts_at": event_date,
                "venue": "Simulated Venue",
                "sport": sport,
                "league": league
            }]
        
        return []
    
    def _match_event(
        self,
        teams: List[str],
        candidate_market: CandidateMarket,
        espn_events: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Encuentra el evento que mejor coincide."""
        best_match = None
        best_score = 0.0
        
        for event in espn_events:
            score = self._calculate_match_score(teams, candidate_market, event)
            if score > best_score:
                best_score = score
                best_match = event
        
        return best_match if best_score >= 0.7 else None
    
    def _calculate_match_score(
        self,
        teams: List[str],
        candidate_market: CandidateMarket,
        event: Dict[str, Any]
    ) -> float:
        """Calcula el score de matching entre mercado y evento."""
        event_teams = event.get("teams", [])
        team_score = self._calculate_team_match(teams, event_teams)
        
        event_date = event.get("starts_at")
        market_date = candidate_market.event_start_time or candidate_market.close_time
        date_score = self._calculate_date_match(market_date, event_date)
        
        league_score = 1.0  # Asumido correcto si llegamos aquí
        
        return 0.6 * team_score + 0.25 * date_score + 0.15 * league_score
    
    def _calculate_team_match(self, teams1: List[str], teams2: List[str]) -> float:
        """Calcula coincidencia de equipos."""
        if not teams1 or not teams2:
            return 0.0
        
        # Normalizar a sets para comparación
        set1 = set(t.lower() for t in teams1)
        set2 = set(t.lower() for t in teams2)
        
        # Coincidencia exacta
        if set1 == set2:
            return 1.0
        
        # Coincidencia parcial
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _calculate_date_match(self, date1: Optional[datetime], date2: Optional[datetime]) -> float:
        """Calcula coincidencia de fechas."""
        if not date1 or not date2:
            return 0.5  # Confianza media si falta fecha
        
        # Calcular diferencia en horas
        diff_hours = abs((date1 - date2).total_seconds() / 3600)
        
        # Score basado en diferencia
        if diff_hours <= 1:
            return 1.0
        elif diff_hours <= 2:
            return 0.9
        elif diff_hours <= 6:
            return 0.7
        elif diff_hours <= 24:
            return 0.5
        else:
            return max(0.0, 1.0 - (diff_hours / 168))  # Degradación lineal hasta 1 semana

