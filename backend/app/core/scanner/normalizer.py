"""
Normalización y enriquecimiento de datos del Scanner.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
import re
from app.core.scanner.models import CandidateMarket, Outcome, EventMetadata


class ScannerNormalizer:
    """Normalizador y enriquecedor de mercados."""
    
    # Patrones para detección de equipos
    TEAM_PATTERNS = [
        r"(\w+)\s+vs\s+(\w+)",  # "Lakers vs Celtics"
        r"(\w+)\s+v\s+(\w+)",   # "Lakers v Celtics"
        r"(\w+)\s+@\s+(\w+)",   # "Lakers @ Celtics"
    ]
    
    # Patrones para detección de fechas
    DATE_PATTERNS = [
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{1,2}):?(\d{2})?\s*(AM|PM)?\s*(ET|PT|CT|MT)?",
        r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):?(\d{2})?\s*(ET|PT|CT|MT)?",
    ]
    
    # Mapeo de meses
    MONTH_MAP = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    def normalize_outcome_name(self, name: str) -> str:
        """
        Normaliza nombre de outcome.
        
        "Yes" -> "YES"
        "No" -> "NO"
        "True" -> "YES"
        "False" -> "NO"
        """
        name_lower = name.lower().strip()
        if name_lower in ["yes", "true", "1"]:
            return "YES"
        elif name_lower in ["no", "false", "0"]:
            return "NO"
        return name.upper()
    
    def normalize_outcomes(self, outcomes: List[Dict[str, Any]]) -> List[Outcome]:
        """
        Normaliza y convierte outcomes a objetos Outcome.
        
        Args:
            outcomes: Lista de outcomes raw
        
        Returns:
            Lista de Outcome normalizados
        """
        normalized = []
        
        for outcome in outcomes:
            name = self.normalize_outcome_name(outcome.get("name", ""))
            price = float(outcome.get("price") or outcome.get("current_price", 0.0))
            liquidity = float(outcome.get("liquidity") or outcome.get("total_liquidity", 0.0))
            volume_24h = float(outcome.get("volume_24h") or outcome.get("volume24h", 0.0))
            
            # Validar precio
            if price < 0.0 or price > 1.0:
                continue  # Skip invalid prices
            
            normalized.append(Outcome(
                name=name,
                price=price,
                liquidity=liquidity,
                volume_24h=volume_24h
            ))
        
        # Ordenar por precio (mayor a menor)
        normalized.sort(key=lambda x: x.price, reverse=True)
        
        return normalized
    
    def normalize_category(self, category: Optional[str]) -> str:
        """
        Normaliza categoría a minúsculas y sin espacios extra.
        """
        if not category:
            return "unknown"
        return category.lower().strip()
    
    def normalize_subcategory(self, subcategory: Optional[str]) -> Optional[str]:
        """
        Normaliza subcategoría.
        """
        if not subcategory:
            return None
        return subcategory.lower().strip()
    
    def extract_event_metadata(self, question: str, description: Optional[str] = None) -> EventMetadata:
        """
        Extrae metadata del evento desde el título/descripción.
        
        Args:
            question: Pregunta del mercado
            description: Descripción (opcional)
        
        Returns:
            EventMetadata con información extraída
        """
        text = f"{question} {description or ''}".strip()
        
        # Detectar equipos
        teams = self._detect_teams(text)
        
        # Detectar deporte
        sport = self._detect_sport(text, teams)
        
        # Parsear fecha
        event_time, timezone = self._parse_event_time(text)
        
        # Calcular confianza
        confidence = self._calculate_confidence(teams, sport, event_time)
        
        return EventMetadata(
            detected_teams=teams,
            detected_sport=sport,
            event_start_time_parsed=event_time,
            timezone=timezone,
            raw_text=text,
            confidence=confidence
        )
    
    def _detect_teams(self, text: str) -> List[str]:
        """Detecta equipos en el texto."""
        teams = []
        
        for pattern in self.TEAM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    teams.extend([m.strip() for m in match if m.strip()])
                else:
                    teams.append(match.strip())
        
        # Remover duplicados y normalizar
        teams = list(set([t.title() for t in teams if len(t) > 2]))
        
        return teams[:2]  # Solo primeros 2 equipos
    
    def _detect_sport(self, text: str, teams: List[str] = None) -> Optional[str]:
        """Detecta tipo de deporte."""
        text_lower = text.lower()
        
        # Detección por palabras clave
        if any(word in text_lower for word in ["basketball", "nba", "lakers", "celtics", "warriors"]):
            return "basketball"
        elif any(word in text_lower for word in ["football", "nfl", "super bowl"]):
            return "football"
        elif any(word in text_lower for word in ["soccer", "futbol", "premier league"]):
            return "soccer"
        elif any(word in text_lower for word in ["baseball", "mlb"]):
            return "baseball"
        
        return None
    
    def _parse_event_time(self, text: str) -> tuple[Optional[datetime], Optional[str]]:
        """Parsea fecha del evento desde el texto."""
        # Por ahora, retornar None (se puede mejorar con parsing más sofisticado)
        # TODO: Implementar parsing de fechas con los patrones definidos
        return (None, None)
    
    def _calculate_confidence(self, teams: List[str], sport: Optional[str], event_time: Optional[datetime]) -> float:
        """Calcula confianza en el parsing."""
        confidence = 0.0
        
        if teams:
            confidence += 0.4
        if sport:
            confidence += 0.3
        if event_time:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def calculate_market_hash(self, polymarket_id: str, question: str, outcomes: List[Outcome]) -> str:
        """
        Calcula hash del mercado para tracking.
        
        Args:
            polymarket_id: ID de Polymarket
            question: Pregunta del mercado
            outcomes: Lista de outcomes
        
        Returns:
            Hash SHA256
        """
        # Crear string para hashing
        outcome_str = json.dumps([{"name": o.name, "price": o.price} for o in outcomes], sort_keys=True)
        hash_input = f"{polymarket_id}:{question}:{outcome_str}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def normalize_market(
        self,
        market: Dict[str, Any],
        trace_id: str,
        event_metadata: Optional[EventMetadata] = None
    ) -> CandidateMarket:
        """
        Normaliza un mercado raw a CandidateMarket.
        
        Args:
            market: Mercado raw de Polymarket
            trace_id: ID de trazabilidad
            event_metadata: Metadata del evento (opcional, se genera si no se provee)
        
        Returns:
            CandidateMarket normalizado
        """
        # Normalizar outcomes
        outcomes = self.normalize_outcomes(market.get("outcomes", []))
        
        if len(outcomes) != 2:
            raise ValueError(f"Market must have exactly 2 outcomes, got {len(outcomes)}")
        
        # Calcular precios consolidados
        best_yes_price = max(o.price for o in outcomes if o.name == "YES")
        best_no_price = max(o.price for o in outcomes if o.name == "NO")
        spread = abs(best_yes_price - best_no_price)
        
        # Normalizar categorías
        category = self.normalize_category(market.get("category"))
        subcategory = self.normalize_subcategory(market.get("subcategory"))
        
        # Extraer metadata del evento si no se provee
        if event_metadata is None:
            question = market.get("question", "")
            description = market.get("description")
            event_metadata = self.extract_event_metadata(question, description)
        
        # Calcular hash
        market_hash = self.calculate_market_hash(
            market.get("id", ""),
            market.get("question", ""),
            outcomes
        )
        
        # Calcular volumen y liquidez total
        volume_24h = sum(o.volume_24h for o in outcomes)
        liquidity_total = sum(o.liquidity for o in outcomes)
        
        # Extraer condition_id y clobTokenIds de la respuesta de Polymarket API
        condition_id = market.get("conditionId") or market.get("condition_id")
        clob_token_ids = None
        
        # clobTokenIds puede venir como string (JSON) o como dict
        clob_token_ids_raw = market.get("clobTokenIds")
        if clob_token_ids_raw:
            if isinstance(clob_token_ids_raw, str):
                try:
                    import json
                    clob_token_ids = json.loads(clob_token_ids_raw)
                except (json.JSONDecodeError, TypeError):
                    # Si no es JSON válido, intentar parsear como string simple
                    clob_token_ids = None
            elif isinstance(clob_token_ids_raw, dict):
                clob_token_ids = clob_token_ids_raw
            elif isinstance(clob_token_ids_raw, list) and len(clob_token_ids_raw) >= 2:
                # Si viene como lista [token_yes, token_no], convertir a dict
                clob_token_ids = {
                    "YES": str(clob_token_ids_raw[0]),
                    "NO": str(clob_token_ids_raw[1])
                }
        
        # Timestamps
        now = datetime.utcnow()
        created_at = market.get("created_at")
        if isinstance(created_at, str):
            # TODO: Parsear fecha desde string
            created_at = now
        elif not isinstance(created_at, datetime):
            created_at = now
        
        return CandidateMarket(
            polymarket_id=market.get("id") or market.get("market_id", ""),
            trace_id=trace_id,
            question=market.get("question", ""),
            description=market.get("description"),
            category=category,
            subcategory=subcategory,
            created_at=created_at,
            close_time=None,  # TODO: Parsear desde market
            event_start_time=event_metadata.event_start_time_parsed,
            outcomes=outcomes,
            best_yes_price=best_yes_price,
            best_no_price=best_no_price,
            spread=spread,
            status=market.get("status", "OPEN"),
            is_binary=True,
            event_metadata=event_metadata,
            volume_24h=volume_24h,
            liquidity_total=liquidity_total,
            market_hash=market_hash,
            condition_id=condition_id,
            clob_token_ids=clob_token_ids,
            scanned_at=now,
            updated_at=now
        )

