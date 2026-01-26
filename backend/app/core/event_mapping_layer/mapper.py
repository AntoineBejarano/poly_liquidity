"""
Event Mapping Layer - orquesta clasificación y mapeo de eventos.
"""
from typing import List, Optional
from uuid import UUID
from app.core.scanner.models import CandidateMarket
from app.core.event_mapping_layer.models import EventDescriptor, EventType
from app.core.event_mapping_layer.classifiers.sports_classifier import SportsClassifier
from app.core.event_mapping_layer.mappers.sports_mapper import SportsMapper


class EventMappingLayer:
    """
    Capa de mapeo de eventos.
    
    Responsabilidades:
    - Clasificar mercados por tipo de evento
    - Mapear mercados a eventos reales verificables
    - Calcular confianza del mapping
    - Generar EventDescriptor estandarizado
    """
    
    def __init__(self):
        """Inicializa el Event Mapping Layer."""
        # Classifiers
        self.sports_classifier = SportsClassifier()
        
        # Mappers
        self.sports_mapper = SportsMapper()
    
    async def map_market(self, candidate_market: CandidateMarket) -> EventDescriptor:
        """
        Mapea un mercado candidato a un evento real.
        
        Args:
            candidate_market: Mercado candidato del Scanner
        
        Returns:
            EventDescriptor con el resultado del mapping
        """
        trace_id = candidate_market.trace_id
        
        # Paso 1: Clasificar tipo de evento
        event_type = self._classify_event_type(candidate_market)
        
        # Paso 2: Mapear según tipo
        if event_type == EventType.SPORTS:
            return await self.sports_mapper.map(candidate_market, str(trace_id))
        else:
            # Para otros tipos, retornar descriptor sin mapear
            return EventDescriptor(
                market_id=candidate_market.polymarket_id,
                mapped=False,
                event_type=event_type,
                mapping_confidence=0.0,
                reason=f"no_mapper_for_{event_type}",
                trace_id=trace_id,
                metadata={}
            )
    
    async def map_markets(self, candidate_markets: List[CandidateMarket]) -> List[EventDescriptor]:
        """
        Mapea múltiples mercados candidatos.
        
        Args:
            candidate_markets: Lista de mercados candidatos
        
        Returns:
            Lista de EventDescriptor
        """
        descriptors = []
        for market in candidate_markets:
            descriptor = await self.map_market(market)
            descriptors.append(descriptor)
        return descriptors
    
    def _classify_event_type(self, candidate_market: CandidateMarket) -> str:
        """
        Clasifica el tipo de evento de un mercado.
        
        Args:
            candidate_market: Mercado candidato
        
        Returns:
            Tipo de evento (sports, politics, crypto, etc.)
        """
        # Intentar clasificar como sports
        if self.sports_classifier.classify(candidate_market) == EventType.SPORTS:
            return EventType.SPORTS
        
        # Por defecto, unknown
        return EventType.UNKNOWN
