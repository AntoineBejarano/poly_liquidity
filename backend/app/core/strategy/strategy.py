"""
Strategy Engine - Lógica de decisión de entradas en mercados.

Refactorizado según especificación en docs/services/strategy.md
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from app.core.state import state
from app.core.config_service import config_service
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.core.runtime_supervisor import RuntimeMode
from app.core.strategy.models import (
    OrderIntent, NoEntryReason, MarketState, EventState, StrategyConfig
)

logger = logging.getLogger(__name__)


class Strategy:
    """
    Strategy Engine service.
    
    Responsabilidades:
    - Analizar mercados mapeados y con eventos monitorizados
    - Identificar momentos de entrada óptimos
    - Determinar precio objetivo y tamaño
    - Generar Order Intents
    """
    
    def __init__(self):
        """Inicializa el Strategy Engine."""
        self._last_intents: List[OrderIntent] = []
        self._last_no_entry_reasons: List[NoEntryReason] = []
        self._config: Optional[StrategyConfig] = None
    
    def _get_config(self) -> StrategyConfig:
        """Obtiene la configuración de la estrategia."""
        if self._config is None:
            risk_config = state.risk_config
            self._config = StrategyConfig(
                min_entry_price=risk_config.min_entry_price,
                max_entry_spread=risk_config.target_margin * 20,  # Aproximación
                safety_tick=risk_config.safety_tick,
                target_edge=risk_config.target_margin,
                max_order_size=risk_config.max_single_order_size,
                max_exposure_per_market=risk_config.max_exposure_per_market,
                max_global_exposure=risk_config.max_global_exposure,
                latency_mode="GREEN",  # Se obtiene dinámicamente
                aggressive_mode=False  # Configurable
            )
        return self._config
    
    def _check_activation_conditions(
        self,
        market_id: UUID,
        market_state: MarketState,
        event_state: EventState,
        trace_id: UUID
    ) -> tuple[bool, str, Dict[str, Any]]:
        """
        Verifica condiciones de activación.
        
        Returns:
            Tupla (should_enter, reason, details)
        """
        config = self._get_config()
        details = {}
        
        # Condición 1: Evento terminado
        if event_state.event_status not in ["FINISHED_CONFIRMED", "FINISHED_UNCONFIRMED"]:
            return False, "event_not_finished", {
                "event_status": event_state.event_status,
                "required_status": "FINISHED_CONFIRMED"
            }
        
        # Modo agresivo: permitir FINISHED_UNCONFIRMED con alta confianza
        if event_state.event_status == "FINISHED_UNCONFIRMED":
            if not config.aggressive_mode:
                return False, "event_unconfirmed", {
                    "event_status": "FINISHED_UNCONFIRMED",
                    "aggressive_mode": False
                }
            if event_state.confidence_score < 0.85:
                return False, "event_unconfirmed_low_confidence", {
                    "event_status": "FINISHED_UNCONFIRMED",
                    "confidence": event_state.confidence_score,
                    "min_confidence": 0.85
                }
        
        # Condición 2: Precio atractivo
        if market_state.best_ask < config.min_entry_price:
            return False, "ask_price_too_low", {
                "best_ask": market_state.best_ask,
                "min_price_required": config.min_entry_price
            }
        
        # Condición 3: Spread razonable
        if market_state.spread > config.max_entry_spread:
            return False, "spread_too_wide", {
                "spread": market_state.spread,
                "max_spread": config.max_entry_spread
            }
        
        # Condición 4: Latencia apta
        latency_status = latency_monitor.get_status()
        # También verificar runtime mode (lazy import para evitar circular dependency)
        try:
            import app.main as main_module
            runtime_supervisor = main_module.runtime_supervisor
            runtime_mode = runtime_supervisor.get_mode()
        except (AttributeError, ImportError):
            # En tests o si no está disponible, usar modo GREEN por defecto
            from app.core.runtime_supervisor import RuntimeMode
            runtime_mode = RuntimeMode.GREEN
        
        if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED:
            return False, "latency_too_high", {
                "latency_status": latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
                "runtime_mode": runtime_mode.value if hasattr(runtime_mode, 'value') else str(runtime_mode),
                "required_status": "GREEN"
            }
        
        # Todas las condiciones cumplidas
        return True, "conditions_met", {}
    
    def _calculate_target_price(
        self,
        best_ask: float,
        best_bid: float,
        latency_status: LatencyStatus
    ) -> float:
        """
        Calcula precio objetivo con ajustes por latencia.
        
        Según especificación en docs/services/strategy.md
        """
        config = self._get_config()
        
        # Ajustar safety_tick según latencia
        effective_safety_tick = config.safety_tick
        if latency_status == LatencyStatus.YELLOW:
            effective_safety_tick = config.safety_tick * 2.0
        elif latency_status == LatencyStatus.RED:
            effective_safety_tick = config.safety_tick * 3.0
        
        # Fórmula base
        safe_price = best_ask - effective_safety_tick
        max_price = 1.0 - config.target_edge
        
        target_price = min(safe_price, max_price)
        
        # Asegurar que no esté por debajo del best_bid
        target_price = max(target_price, best_bid)
        
        # Validación final
        if target_price < config.min_entry_price:
            return 0.0  # No entrar
        
        return target_price
    
    def _calculate_size(
        self,
        market_id: UUID,
        target_price: float,
        orderbook_liquidity: float,
        event_state: EventState,
        latency_status: LatencyStatus
    ) -> float:
        """
        Calcula tamaño de orden con ajustes por latencia y exposición.
        
        Según especificación en docs/services/strategy.md
        """
        config = self._get_config()
        
        # RED: No crear orden
        if latency_status == LatencyStatus.RED:
            return 0.0
        
        # 1. Exposición restante por mercado
        current_exposure = 0.0
        if market_id in state.exposures:
            current_exposure = state.exposures[market_id].notional
        
        remaining_market = config.max_exposure_per_market - current_exposure
        size_from_capacity = remaining_market / target_price if target_price > 0 else 0.0
        
        # 2. Liquidez en orderbook
        size_from_liquidity = orderbook_liquidity
        
        # 3. Tamaño máximo por orden
        max_single = config.max_order_size / target_price if target_price > 0 else 0.0
        
        # 4. Exposición global restante
        global_exposure = sum(
            exp.notional for exp in state.exposures.values()
        )
        remaining_global = config.max_global_exposure - global_exposure
        size_from_global = remaining_global / target_price if target_price > 0 else 0.0
        
        # Tomar el mínimo
        base_size = min(
            size_from_capacity,
            size_from_liquidity,
            max_single,
            size_from_global
        )
        
        # Ajustes por latencia
        if latency_status == LatencyStatus.YELLOW:
            base_size = base_size * 0.5
        
        # Ajustes por confianza (FINISHED_UNCONFIRMED)
        if event_state.event_status == "FINISHED_UNCONFIRMED":
            if event_state.confidence_score >= 0.85:
                base_size = base_size * 0.5
            else:
                base_size = 0.0
        
        # Aplicar heurísticas para sports
        if event_state.event_type == "sports":
            base_size = self._apply_sports_heuristics(base_size, event_state, config)
        
        return max(0.0, base_size)
    
    def _apply_sports_heuristics(
        self,
        base_size: float,
        event_state: EventState,
        config: StrategyConfig
    ) -> float:
        """
        Aplica heurísticas adicionales para eventos deportivos.
        
        Según especificación en docs/services/strategy.md
        """
        size = base_size
        
        # Heurística 1: Evento con final reciente
        if event_state.event_finished_at:
            time_since_finished = datetime.utcnow() - event_state.event_finished_at
            if time_since_finished > timedelta(minutes=10):
                # Entradas menos agresivas
                size = size * 0.7
                # safety_tick ya se ajusta en _calculate_target_price
        
        # Heurística 2: Múltiples fuentes coinciden
        sources_finished = [
            source for source, status in event_state.sources_state.items()
            if status == "FINISHED"
        ]
        if len(sources_finished) >= 3:
            # Permitir entradas más agresivas
            size = size * 1.1
        
        return size
    
    def _get_orderbook_liquidity(self, market_id: UUID, target_price: float) -> float:
        """
        Obtiene liquidez disponible en orderbook al precio objetivo.
        
        TODO: Implementar parsing real del orderbook
        """
        if market_id in state.markets:
            market_state = state.markets[market_id]
            if market_state.orderbook_snapshot:
                # Parse orderbook para encontrar liquidez al target_price
                # Por ahora, retornar estimación
                return market_state.orderbook_snapshot.get("liquidity_at_price", {}).get(
                    str(target_price), 10000.0
                )
        
        # Default liquidity estimate
        return 10000.0
    
    def _create_market_state_from_internal(self, market_id: UUID) -> Optional[MarketState]:
        """
        Crea MarketState desde el estado interno.
        
        Convierte el MarketState interno a la estructura esperada.
        """
        if market_id not in state.markets:
            return None
        
        internal_state = state.markets[market_id]
        
        # Calcular best_ask y best_bid desde last_price y spread
        best_ask = internal_state.last_price + (internal_state.spread or 0.0) / 2
        best_bid = internal_state.last_price - (internal_state.spread or 0.0) / 2
        
        return MarketState(
            market_id=market_id,
            best_bid=best_bid,
            best_ask=best_ask,
            last_price=internal_state.last_price or 0.0,
            spread=internal_state.spread or 0.0,
            outcomes=["YES", "NO"],
            open_interest=None,
            orderbook_snapshot=internal_state.orderbook_snapshot,
            close_time=None,
            volume_24h=internal_state.volume
        )
    
    def _create_event_state_from_internal(self, market_id: UUID) -> Optional[EventState]:
        """
        Crea EventState desde el estado interno.
        
        Convierte el EventState interno a la estructura esperada.
        """
        if market_id not in state.events:
            return None
        
        internal_state = state.events[market_id]
        
        return EventState(
            event_status=internal_state.state,
            confidence_score=internal_state.confidence,
            sources_state={},  # TODO: Obtener desde Event Watch Engine
            event_finished_at=internal_state.finished_at,
            last_update=internal_state.updated_at or datetime.utcnow(),
            event_type=None  # TODO: Obtener desde Event Watch Engine
        )
    
    async def tick(self) -> List[OrderIntent]:
        """
        Decide sobre órdenes basándose en:
        - Market state
        - Event state
        - Exposure state
        
        Returns:
            Lista de OrderIntents (órdenes propuestas)
        """
        intents: List[OrderIntent] = []
        no_entry_reasons: List[NoEntryReason] = []
        trace_id = uuid4()
        
        config = self._get_config()
        latency_status = latency_monitor.get_status()
        
        # Iterar por mercados en estado
        for market_id, _ in state.markets.items():
            # Crear MarketState desde estado interno
            market_state = self._create_market_state_from_internal(market_id)
            if not market_state:
                continue
            
            # Crear EventState desde estado interno
            event_state = self._create_event_state_from_internal(market_id)
            if not event_state:
                no_entry_reasons.append(NoEntryReason(
                    market_id=market_id,
                    reason="no_event_state",
                    details={"message": "Event state not available"},
                    trace_id=trace_id
                ))
                continue
            
            # Verificar condiciones de activación
            should_enter, reason, details = self._check_activation_conditions(
                market_id, market_state, event_state, trace_id
            )
            
            if not should_enter:
                no_entry_reasons.append(NoEntryReason(
                    market_id=market_id,
                    reason=reason,
                    details=details,
                    trace_id=trace_id
                ))
                logger.debug(
                    f"Market {market_id}: No entry - {reason}",
                    extra={"market_id": str(market_id), "reason": reason, "details": details, "trace_id": str(trace_id)}
                )
                continue
            
            # Calcular precio objetivo
            target_price = self._calculate_target_price(
                market_state.best_ask,
                market_state.best_bid,
                latency_status
            )
            
            if target_price == 0.0:
                no_entry_reasons.append(NoEntryReason(
                    market_id=market_id,
                    reason="target_price_too_low",
                    details={
                        "calculated_price": target_price,
                        "min_price_required": config.min_entry_price
                    },
                    trace_id=trace_id
                ))
                continue
            
            # Obtener liquidez del orderbook
            liquidity = self._get_orderbook_liquidity(market_id, target_price)
            
            if liquidity < config.min_liquidity_required:
                no_entry_reasons.append(NoEntryReason(
                    market_id=market_id,
                    reason="insufficient_liquidity",
                    details={
                        "available_liquidity": liquidity,
                        "min_required": config.min_liquidity_required
                    },
                    trace_id=trace_id
                ))
                continue
            
            # Calcular tamaño
            size = self._calculate_size(
                market_id,
                target_price,
                liquidity,
                event_state,
                latency_status
            )
            
            # Solo crear intent si size > 0
            if size > 0:
                intent = OrderIntent(
                    market_id=market_id,
                    side="BUY",
                    price=target_price,
                    size=size,
                    reason="conditions_met",
                    metadata={
                        "best_ask": market_state.best_ask,
                        "best_bid": market_state.best_bid,
                        "safety_tick_applied": config.safety_tick,
                        "latency_status": latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
                        "event_confidence": event_state.confidence_score,
                        "event_status": event_state.event_status
                    },
                    trace_id=trace_id
                )
                intents.append(intent)
                
                logger.info(
                    f"Created order intent for market {market_id}",
                    extra={
                        "market_id": str(market_id),
                        "price": target_price,
                        "size": size,
                        "trace_id": str(trace_id)
                    }
                )
            else:
                no_entry_reasons.append(NoEntryReason(
                    market_id=market_id,
                    reason="size_too_small",
                    details={
                        "calculated_size": size,
                        "min_size": 0.0
                    },
                    trace_id=trace_id
                ))
        
        self._last_intents = intents
        self._last_no_entry_reasons = no_entry_reasons
        
        return intents

