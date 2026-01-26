"""
Base mapper para Event Mapping Layer.
"""
from abc import ABC, abstractmethod
from app.core.scanner.models import CandidateMarket
from app.core.event_mapping_layer.models import EventDescriptor


class BaseMapper(ABC):
    """Clase base para mappers de eventos."""
    
    @abstractmethod
    async def map(self, candidate_market: CandidateMarket, trace_id: str) -> EventDescriptor:
        """
        Mapea un mercado candidato a un evento real.
        
        Args:
            candidate_market: Mercado candidato del Scanner
            trace_id: ID de trazabilidad
        
        Returns:
            EventDescriptor con el resultado del mapping
        """
        pass
    
    @abstractmethod
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
        pass

