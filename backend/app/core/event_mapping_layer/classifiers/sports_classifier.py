"""
Sports Classifier - clasifica mercados como eventos deportivos.
"""
import re
from typing import Literal
from app.core.scanner.models import CandidateMarket
from app.core.event_mapping_layer.classifiers.base_classifier import BaseClassifier


class SportsClassifier(BaseClassifier):
    """Classifier para eventos deportivos."""
    
    # Patrones para detectar eventos deportivos
    SPORTS_PATTERNS = [
        r"\bvs\.?\b",  # "vs" o "vs."
        r"\b@\b",      # "@"
        r"\bwin\b",    # "win"
        r"\bscore\b",  # "score"
        r"\btotal points\b",  # "total points"
        r"\bover/under\b",    # "over/under"
    ]
    
    # Palabras clave deportivas
    SPORTS_KEYWORDS = [
        "nba", "nfl", "mlb", "nhl", "soccer", "football",
        "basketball", "baseball", "hockey", "tennis",
        "championship", "playoff", "super bowl", "world cup"
    ]
    
    def classify(self, candidate_market: CandidateMarket) -> Literal[
        "sports", "politics", "crypto",
        "finance", "weather", "custom", "unknown"
    ]:
        """
        Clasifica un mercado como evento deportivo.
        
        Args:
            candidate_market: Mercado candidato
        
        Returns:
            "sports" si es deportivo, "unknown" si no
        """
        # Verificar categoría
        if candidate_market.category.lower() == "sports":
            return "sports"
        
        # Verificar subcategoría
        if candidate_market.subcategory:
            subcat_lower = candidate_market.subcategory.lower()
            if any(keyword in subcat_lower for keyword in ["basketball", "football", "soccer", "baseball", "hockey"]):
                return "sports"
        
        # Verificar pregunta por patrones
        question_lower = candidate_market.question.lower()
        
        # Buscar patrones
        for pattern in self.SPORTS_PATTERNS:
            if re.search(pattern, question_lower):
                return "sports"
        
        # Buscar palabras clave
        for keyword in self.SPORTS_KEYWORDS:
            if keyword in question_lower:
                return "sports"
        
        # Verificar metadata del evento (si tiene equipos detectados)
        if candidate_market.event_metadata and candidate_market.event_metadata.detected_teams:
            return "sports"
        
        return "unknown"
    
    def get_confidence(self, candidate_market: CandidateMarket) -> float:
        """
        Calcula la confianza de que es un evento deportivo.
        
        Args:
            candidate_market: Mercado candidato
        
        Returns:
            Confianza (0.0 - 1.0)
        """
        confidence = 0.0
        
        # Categoría = "sports" → alta confianza
        if candidate_market.category.lower() == "sports":
            confidence += 0.5
        
        # Subcategoría deportiva → alta confianza
        if candidate_market.subcategory:
            subcat_lower = candidate_market.subcategory.lower()
            if any(keyword in subcat_lower for keyword in ["basketball", "football", "soccer", "baseball", "hockey"]):
                confidence += 0.3
        
        # Patrones en pregunta → confianza media
        question_lower = candidate_market.question.lower()
        pattern_count = sum(1 for pattern in self.SPORTS_PATTERNS if re.search(pattern, question_lower))
        if pattern_count > 0:
            confidence += 0.2 * min(pattern_count, 2)  # Máximo 0.4
        
        # Equipos detectados → confianza alta
        if candidate_market.event_metadata and candidate_market.event_metadata.detected_teams:
            confidence += 0.2
        
        return min(confidence, 1.0)

