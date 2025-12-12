"""
Event State Aggregator - Agrega resultados de checkers usando quorum rules.

Según especificación en docs/services/event_watch_engine.md
"""
from typing import List, Dict, Tuple
from datetime import datetime
from app.core.checkers.base import CheckerResult
from app.core.event_watch_engine.models import EventState, EventStateType, WatchEngineConfig


class StateAggregator:
    """
    Agrega resultados de checkers usando reglas de quorum.
    
    Responsabilidades:
    - Combinar resultados de múltiples checkers
    - Aplicar reglas de quorum
    - Calcular confianza agregada
    - Determinar estado final (LIVE, FINISHED_CONFIRMED, FINISHED_UNCONFIRMED, UNKNOWN)
    """
    
    def __init__(self, config: WatchEngineConfig):
        """
        Inicializa el agregador.
        
        Args:
            config: Configuración del Watch Engine
        """
        self.config = config
    
    def aggregate(
        self,
        checker_results: List[CheckerResult],
        event_id: str,
        trace_id: str = None
    ) -> EventState:
        """
        Agrega resultados de checkers y determina estado final.
        
        Args:
            checker_results: Lista de resultados de checkers
            event_id: ID del evento
            trace_id: ID de trazabilidad (opcional)
        
        Returns:
            EventState con estado agregado
        """
        if not checker_results:
            return EventState(
                event_id=event_id,
                state=EventStateType.UNKNOWN,
                confidence=0.0,
                last_update=datetime.utcnow(),
                trace_id=trace_id
            )
        
        # Separar resultados por estado
        finished_results = [r for r in checker_results if r.state == "FINISHED"]
        live_results = [r for r in checker_results if r.state == "LIVE"]
        unknown_results = [r for r in checker_results if r.state == "UNKNOWN"]
        
        # Filtrar por confianza mínima
        high_confidence_finished = [
            r for r in finished_results
            if r.confidence >= self.config.min_confidence_threshold
        ]
        high_confidence_live = [
            r for r in live_results
            if r.confidence >= self.config.min_confidence_threshold
        ]
        
        # Construir mapa de fuentes
        sources = {}
        for result in checker_results:
            sources[result.source] = result.state
        
        # Aplicar reglas de quorum
        state, confidence = self._apply_quorum_rules(
            high_confidence_finished,
            high_confidence_live,
            unknown_results,
            checker_results
        )
        
        # Determinar finished_at si está FINISHED
        finished_at = None
        if state in [EventStateType.FINISHED_CONFIRMED, EventStateType.FINISHED_UNCONFIRMED]:
            # Usar el finished_at más temprano de los checkers que dicen FINISHED
            finished_times = [
                r.finished_at for r in finished_results
                if r.finished_at is not None
            ]
            if finished_times:
                finished_at = min(finished_times)
        
        return EventState(
            event_id=event_id,
            state=state,
            confidence=confidence,
            sources=sources,
            last_update=datetime.utcnow(),
            finished_at=finished_at,
            checker_results=checker_results,
            trace_id=trace_id
        )
    
    def _apply_quorum_rules(
        self,
        high_confidence_finished: List[CheckerResult],
        high_confidence_live: List[CheckerResult],
        unknown_results: List[CheckerResult],
        all_results: List[CheckerResult]
    ) -> Tuple[EventStateType, float]:
        """
        Aplica reglas de quorum para determinar estado final.
        
        Reglas según especificación:
        - FINISHED_CONFIRMED: 2+ checkers dicen FINISHED con confianza >= threshold
        - FINISHED_UNCONFIRMED: 1 checker dice FINISHED con confianza >= threshold, o 2+ con confianza < threshold
        - LIVE: Ningún checker detecta FINISHED, al menos 1 dice LIVE
        - UNKNOWN: Todos los checkers fallan o no hay datos suficientes
        
        Returns:
            Tupla (EventStateType, confidence)
        """
        # FINISHED_CONFIRMED: 2+ checkers con alta confianza dicen FINISHED
        if len(high_confidence_finished) >= self.config.min_checkers_for_confirmed:
            confidence = self._calculate_weighted_confidence(high_confidence_finished)
            return EventStateType.FINISHED_CONFIRMED, confidence
        
        # FINISHED_UNCONFIRMED: 1 checker con alta confianza dice FINISHED
        # O 2+ checkers con baja confianza dicen FINISHED
        finished_all = [r for r in all_results if r.state == "FINISHED"]
        if len(high_confidence_finished) == 1:
            confidence = high_confidence_finished[0].confidence
            return EventStateType.FINISHED_UNCONFIRMED, confidence
        elif len(finished_all) >= 2:
            # 2+ checkers dicen FINISHED pero con confianza < threshold
            confidence = self._calculate_weighted_confidence(finished_all)
            return EventStateType.FINISHED_UNCONFIRMED, confidence
        
        # LIVE: Al menos 1 checker dice LIVE
        if high_confidence_live:
            confidence = self._calculate_weighted_confidence(high_confidence_live)
            return EventStateType.LIVE, confidence
        
        # UNKNOWN: Todos los checkers fallan o no hay datos suficientes
        if all(r.state == "UNKNOWN" for r in all_results):
            return EventStateType.UNKNOWN, 0.0
        
        # Si hay mezcla de LIVE y UNKNOWN, considerar LIVE con baja confianza
        if live_results:
            confidence = self._calculate_weighted_confidence(live_results) * 0.5  # Reducir confianza
            return EventStateType.LIVE, confidence
        
        # Default: UNKNOWN
        return EventStateType.UNKNOWN, 0.0
    
    def _calculate_weighted_confidence(self, results: List[CheckerResult]) -> float:
        """
        Calcula confianza ponderada por weight de cada checker.
        
        Args:
            results: Lista de resultados de checkers
        
        Returns:
            Confianza promedio ponderada (0.0 - 1.0)
        """
        if not results:
            return 0.0
        
        # Obtener weights de los checkers (asumiendo que están en el resultado)
        # Por ahora, usar promedio simple si no hay weights disponibles
        total_confidence = sum(r.confidence for r in results)
        return total_confidence / len(results)

