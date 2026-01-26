"""
Event State Aggregator - Agrega resultados de checkers usando quorum rules.

Según especificación en docs/services/event_watch_engine.md
"""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from app.core.checkers.base import CheckerResult
from app.core.checkers.health_service import checker_health_service
from app.core.config_service import config_service
from app.core.event_watch_engine.models import EventState, EventStateType, WatchEngineConfig

logger = logging.getLogger(__name__)


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
    
    def _calculate_effective_quorum(
        self,
        quorum_base: int,
        available_checkers: int,
        allow_single_checker: bool,
        allow_zero_checker: bool
    ) -> Tuple[Optional[int], str, bool]:
        """
        Calcula el quorum efectivo basado en checkers disponibles.
        
        Args:
            quorum_base: Quorum base configurado
            available_checkers: Número de checkers saludables disponibles
            allow_single_checker: Permitir quorum de 1
            allow_zero_checker: Permitir sistema sin checkers (sin trading)
            
        Returns:
            Tupla (quorum_efectivo, razon, trading_permitido)
        """
        # 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
        if available_checkers == 0:
            if allow_zero_checker:
                return (None, "no_checkers_available_allow_zero", False)
            else:
                return (None, "no_checkers_available_system_degraded", False)
        
        # Con 1 checker disponible
        if available_checkers == 1:
            if allow_single_checker:
                return (1, "single_checker_allowed", True)
            else:
                # Quorum base puede ser 1, pero con advertencia
                effective = min(quorum_base, 1)
                return (effective, "single_checker_available_quorum_base_applied", True)
        
        # Con 2+ checkers disponibles
        effective = min(quorum_base, available_checkers)
        return (effective, "quorum_base_applied", True)
    
    def aggregate(
        self,
        checker_results: List[CheckerResult],
        event_id: str,
        trace_id: str = None,
        category: str = "sports",
        healthy_checker_ids: Optional[List[str]] = None
    ) -> EventState:
        """
        Agrega resultados de checkers y determina estado final usando quorum dinámico.
        
        Args:
            checker_results: Lista de resultados de checkers
            event_id: ID del evento
            trace_id: ID de trazabilidad (opcional)
            category: Categoría del evento (para obtener checkers saludables)
            healthy_checker_ids: Lista de IDs de checkers saludables (opcional, se calcula si no se proporciona)
        
        Returns:
            EventState con estado agregado incluyendo información de quorum
        """
        if not checker_results:
            # Obtener configuración para determinar comportamiento sin resultados
            allow_zero_checker = config_service.get("allow_zero_checker", False)
            quorum_base = int(config_service.get("quorum_base", 2))
            
            return EventState(
                event_id=event_id,
                state=EventStateType.UNKNOWN,
                confidence=0.0,
                last_update=datetime.utcnow(),
                trace_id=trace_id,
                quorum_used=None,
                quorum_required=quorum_base,
                checkers_available=0,
                checkers_used=0,
                quorum_reason="no_checker_results",
                trading_permitted=False
            )
        
        # Obtener checkers saludables si no se proporcionaron
        if healthy_checker_ids is None:
            healthy_checkers = checker_health_service.get_healthy_checkers(category)
            healthy_checker_ids = [str(c.id) for c in healthy_checkers]
        
        available_count = len(healthy_checker_ids)
        
        # Obtener configuración de quorum
        quorum_base = int(config_service.get("quorum_base", 2))
        allow_single_checker = config_service.get("allow_single_checker", False)
        allow_zero_checker = config_service.get("allow_zero_checker", False)
        min_confidence = float(config_service.get("min_feed_confidence", 0.8))
        
        # Calcular quorum efectivo
        quorum_effective, quorum_reason, trading_permitted = self._calculate_effective_quorum(
            quorum_base=quorum_base,
            available_checkers=available_count,
            allow_single_checker=allow_single_checker,
            allow_zero_checker=allow_zero_checker
        )
        
        # 🔴 REGLA CRÍTICA: Con 0 checkers, NUNCA confirmar FINISHED
        if available_count == 0 or quorum_effective is None:
            return EventState(
                event_id=event_id,
                state=EventStateType.UNKNOWN,
                confidence=0.0,
                sources={},
                last_update=datetime.utcnow(),
                finished_at=None,
                checker_results=checker_results,
                trace_id=trace_id,
                quorum_used=None,
                quorum_required=quorum_base,
                checkers_available=0,
                checkers_used=len(checker_results),
                quorum_reason=quorum_reason,
                trading_permitted=False
            )
        
        # Separar resultados por estado
        finished_results = [r for r in checker_results if r.state == "FINISHED"]
        live_results = [r for r in checker_results if r.state == "LIVE"]
        unknown_results = [r for r in checker_results if r.state == "UNKNOWN"]
        
        # Filtrar por confianza mínima
        high_confidence_finished = [
            r for r in finished_results
            if r.confidence >= min_confidence
        ]
        high_confidence_live = [
            r for r in live_results
            if r.confidence >= min_confidence
        ]
        
        # Construir mapa de fuentes
        sources = {}
        for result in checker_results:
            sources[result.source] = result.state
        
        # Aplicar reglas de quorum dinámicas
        state, confidence = self._apply_quorum_rules(
            high_confidence_finished,
            high_confidence_live,
            unknown_results,
            checker_results,
            quorum_effective
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
        
        # Contar checkers usados (FINISHED con confianza suficiente)
        checkers_used = len(high_confidence_finished)
        
        return EventState(
            event_id=event_id,
            state=state,
            confidence=confidence,
            sources=sources,
            last_update=datetime.utcnow(),
            finished_at=finished_at,
            checker_results=checker_results,
            trace_id=trace_id,
            quorum_used=quorum_effective,
            quorum_required=quorum_base,
            checkers_available=available_count,
            checkers_used=checkers_used,
            quorum_reason=quorum_reason,
            trading_permitted=trading_permitted
        )
    
    def _apply_quorum_rules(
        self,
        high_confidence_finished: List[CheckerResult],
        high_confidence_live: List[CheckerResult],
        unknown_results: List[CheckerResult],
        all_results: List[CheckerResult],
        quorum_effective: int
    ) -> Tuple[EventStateType, float]:
        """
        Aplica reglas de quorum dinámicas para determinar estado final.
        
        Reglas:
        - FINISHED_CONFIRMED: quorum_effective+ checkers dicen FINISHED con confianza >= threshold
        - FINISHED_UNCONFIRMED: 1 checker dice FINISHED con confianza >= threshold (si quorum_effective == 1), o menos que quorum_effective
        - LIVE: Ningún checker detecta FINISHED, al menos 1 dice LIVE
        - UNKNOWN: Todos los checkers fallan o no hay datos suficientes
        
        Args:
            high_confidence_finished: Resultados FINISHED con alta confianza
            high_confidence_live: Resultados LIVE con alta confianza
            unknown_results: Resultados UNKNOWN
            all_results: Todos los resultados
            quorum_effective: Quorum efectivo calculado dinámicamente
            
        Returns:
            Tupla (EventStateType, confidence)
        """
        finished_count = len(high_confidence_finished)
        finished_all = [r for r in all_results if r.state == "FINISHED"]
        live_results = [r for r in all_results if r.state == "LIVE"]
        
        # FINISHED_CONFIRMED: quorum_effective+ checkers con alta confianza dicen FINISHED
        if finished_count >= quorum_effective:
            confidence = self._calculate_weighted_confidence(high_confidence_finished)
            return EventStateType.FINISHED_CONFIRMED, confidence
        
        # FINISHED_UNCONFIRMED: 1 checker con alta confianza dice FINISHED (si quorum_effective == 1)
        # O menos que quorum_effective pero al menos 1
        if finished_count > 0:
            if finished_count == 1 and quorum_effective == 1:
                confidence = high_confidence_finished[0].confidence
                return EventStateType.FINISHED_UNCONFIRMED, confidence
            elif finished_count < quorum_effective:
                # Hay checkers que dicen FINISHED pero no cumplen quorum
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

