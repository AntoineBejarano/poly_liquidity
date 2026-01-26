"""
Base classifier para Event Mapping Layer.
"""
from abc import ABC, abstractmethod
from typing import Literal
from app.core.scanner.models import CandidateMarket


class BaseClassifier(ABC):
    """Clase base para classifiers de eventos."""
    
    @abstractmethod
    def classify(self, candidate_market: CandidateMarket) -> Literal[
        "sports", "politics", "crypto",
        "finance", "weather", "custom", "unknown"
    ]:
        """
        Clasifica un mercado candidato por tipo de evento.
        
        Args:
            candidate_market: Mercado candidato del Scanner
        
        Returns:
            Tipo de evento detectado
        """
        pass
    
    @abstractmethod
    def get_confidence(self, candidate_market: CandidateMarket) -> float:
        """
        Calcula la confianza de la clasificación.
        
        Args:
            candidate_market: Mercado candidato del Scanner
        
        Returns:
            Confianza (0.0 - 1.0)
        """
        pass

