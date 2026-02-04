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
from app.core.decision_trace import decision_trace_service
from app.core.runtime_supervisor import RuntimeMode
from app.core.execution.polymarket_websocket import get_websocket_manager
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
        
        # WebSocket para precios en tiempo real
        self._websocket_manager = None
        self._tracked_asset_ids: Dict[UUID, str] = {}  # market_id -> asset_id (token_id)
        self._setup_market_websocket()
    
    def _setup_market_websocket(self):
        """Configura WebSocket para recibir updates de precios en tiempo real."""
        try:
            manager = get_websocket_manager()
            self._websocket_manager = manager
            
            # Configurar callbacks para updates de mercado
            manager.on_book_update = self._handle_websocket_book_update
            manager.on_price_change = self._handle_websocket_price_change
            
            logger.info("Market WebSocket callbacks configured for Strategy Engine")
        except Exception as e:
            logger.warning(f"Could not setup Market WebSocket: {e}")
    
    def _handle_websocket_book_update(self, book_msg: Dict[str, Any]):
        """Maneja book update desde WebSocket."""
        try:
            market_condition_id = book_msg.get('market')
            asset_id = book_msg.get('asset_id')
            bids = book_msg.get('bids', [])
            asks = book_msg.get('asks', [])
            timestamp = book_msg.get('timestamp')
            
            # Buscar market_id desde condition_id
            # Necesitamos mapear condition_id a nuestro market_id interno
            # Por ahora, buscar en state.markets por polymarket_id
            for market_id, market_state in state.markets.items():
                # TODO: Necesitamos almacenar condition_id en el market para mapear correctamente
                # Por ahora, usar asset_id como referencia
                if asset_id in self._tracked_asset_ids.values():
                    # Actualizar orderbook snapshot
                    if not market_state.orderbook_snapshot:
                        market_state.orderbook_snapshot = {}
                    
                    market_state.orderbook_snapshot.update({
                        'bids': bids,
                        'asks': asks,
                        'timestamp': timestamp,
                        'asset_id': asset_id
                    })
                    
                    # Actualizar best_bid y best_ask
                    if bids:
                        market_state.last_price = float(bids[0].get('price', 0))
                        best_bid = float(bids[0].get('price', 0))
                    else:
                        best_bid = market_state.last_price or 0.0
                    
                    if asks:
                        best_ask = float(asks[0].get('price', 0))
                    else:
                        best_ask = market_state.last_price or 0.0
                    
                    market_state.spread = best_ask - best_bid if (best_ask > 0 and best_bid > 0) else 0.0
                    market_state.updated_at = datetime.utcnow()
                    
                    logger.debug(
                        f"Book update for market {market_id}: bid={best_bid}, ask={best_ask}",
                        extra={
                            "component": "strategy",
                            "event": "websocket_book_update",
                            "market_id": str(market_id)
                        }
                    )
                    break
        except Exception as e:
            logger.error(f"Error handling WebSocket book update: {e}", exc_info=True)
    
    def _handle_websocket_price_change(self, price_msg: Dict[str, Any]):
        """Maneja price change desde WebSocket."""
        try:
            market_condition_id = price_msg.get('market')
            price_changes = price_msg.get('price_changes', [])
            timestamp = price_msg.get('timestamp')
            
            for change in price_changes:
                asset_id = change.get('asset_id')
                best_bid = float(change.get('best_bid', '0'))
                best_ask = float(change.get('best_ask', '0'))
                price = float(change.get('price', '0'))
                
                # Buscar market por asset_id
                for market_id, asset_id_tracked in self._tracked_asset_ids.items():
                    if asset_id_tracked == asset_id and market_id in state.markets:
                        market_state = state.markets[market_id]
                        market_state.last_price = price
                        market_state.spread = best_ask - best_bid if (best_ask > 0 and best_bid > 0) else 0.0
                        market_state.updated_at = datetime.utcnow()
                        
                        logger.debug(
                            f"Price change for market {market_id}: bid={best_bid}, ask={best_ask}, price={price}",
                            extra={
                                "component": "strategy",
                                "event": "websocket_price_change",
                                "market_id": str(market_id),
                                "asset_id": asset_id
                            }
                        )
                        break
        except Exception as e:
            logger.error(f"Error handling WebSocket price change: {e}", exc_info=True)
    
    def subscribe_to_market(self, market_id: UUID, asset_id: str):
        """
        Suscribe a un mercado para recibir updates de precios via WebSocket.
        
        Args:
            market_id: ID interno del mercado
            asset_id: Asset ID (token ID) de Polymarket
        """
        if not self._websocket_manager:
            return
        
        self._tracked_asset_ids[market_id] = asset_id
        
        # Conectar a MARKET channel para este asset
        try:
            self._websocket_manager.connect_market_channel(
                asset_ids=[asset_id],
                market_id=str(market_id)
            )
            logger.info(f"Subscribed to market {market_id} via WebSocket (asset_id: {asset_id})")
        except Exception as e:
            logger.warning(f"Could not subscribe to market {market_id} via WebSocket: {e}")
    
    def _get_config(self) -> StrategyConfig:
        """
        Obtiene la configuración de la estrategia desde ConfigService.
        
        Usa hot reload para obtener siempre la configuración más reciente.
        """
        # Siempre obtener desde ConfigService para hot reload
        return config_service.get_strategy_config()
    
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
        
        # Condición 1: Evento terminado - SOLO FINISHED_CONFIRMED permitido
        # Regla estricta: El sistema SOLO puede crear órdenes cuando event_state == FINISHED_CONFIRMED
        # determinado exclusivamente por el EventEngine con quorum de ≥2 checkers independientes
        if event_state.event_status != "FINISHED_CONFIRMED":
            return False, "event_not_finished", {
                "event_status": event_state.event_status,
                "required_status": "FINISHED_CONFIRMED"
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
            # En tests o si no está disponible, usar modo GREEN por defecto (RuntimeMode importado al inicio del módulo)
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
        
        # Ajustar safety_tick según latencia (desde ConfigService)
        safety_tick_multiplier_yellow = config_service.get("safety_tick_multiplier_yellow", 2.0)
        safety_tick_multiplier_red = config_service.get("safety_tick_multiplier_red", 3.0)
        
        effective_safety_tick = config.safety_tick
        if latency_status == LatencyStatus.YELLOW:
            effective_safety_tick = config.safety_tick * safety_tick_multiplier_yellow
        elif latency_status == LatencyStatus.RED:
            effective_safety_tick = config.safety_tick * safety_tick_multiplier_red
        
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
    
    def _get_available_bank(self) -> float:
        """
        Obtiene el capital disponible (bank) para calcular tamaño de apuesta.
        
        Returns:
            Capital disponible en USDC
        """
        # Calcular equity desde dashboard
        # TODO: Obtener balance real del wallet cuando esté disponible
        base_equity = 1000000.0  # Capital base
        
        # Calcular PnL realizado y no realizado
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        
        for position_state in state.positions.values():
            if position_state.resolved:
                continue
            
            market_state = state.markets.get(position_state.market_id)
            if market_state and market_state.last_price:
                cost_total = position_state.size * position_state.avg_price
                theoretical_value = position_state.size * market_state.last_price
                unrealized_pnl += theoretical_value - cost_total
        
        # Calcular exposición global
        global_exposure = sum(
            exp.notional for exp in state.exposures.values()
        )
        
        # Bank disponible = equity - exposición global
        available_bank = base_equity + realized_pnl + unrealized_pnl - global_exposure
        
        return max(0.0, available_bank)
    
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
        
        # Calcular tamaño base según configuración de apuesta
        base_bet_size_usdc = 0.0
        
        if config.bet_size_mode == "percentage":
            # Modo porcentaje del bank
            if config.bet_size_percentage and config.bet_size_percentage > 0:
                available_bank = self._get_available_bank()
                base_bet_size_usdc = available_bank * (config.bet_size_percentage / 100.0)
        elif config.bet_size_mode == "fixed_range":
            # Modo rango fijo - usar el máximo del rango como tamaño objetivo
            if config.bet_size_max and config.bet_size_max > 0:
                base_bet_size_usdc = config.bet_size_max
            elif config.bet_size_min and config.bet_size_min > 0:
                base_bet_size_usdc = config.bet_size_min
            else:
                # Fallback al comportamiento anterior
                base_bet_size_usdc = config.max_order_size
        
        # Convertir a shares
        base_size_from_bet = base_bet_size_usdc / target_price if target_price > 0 else 0.0
        
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
        
        # Aplicar tamaño mínimo del rango si está configurado
        if config.bet_size_mode == "fixed_range" and config.bet_size_min:
            min_size_from_bet = config.bet_size_min / target_price if target_price > 0 else 0.0
            base_size_from_bet = max(base_size_from_bet, min_size_from_bet)
        
        # Tomar el mínimo entre todas las restricciones
        base_size = min(
            base_size_from_bet,
            size_from_capacity,
            size_from_liquidity,
            max_single,
            size_from_global
        )
        
        # Ajustes por latencia (desde ConfigService)
        yellow_latency_size_factor = config_service.get("yellow_latency_size_factor", 0.5)
        if latency_status == LatencyStatus.YELLOW:
            base_size = base_size * yellow_latency_size_factor
        
        # Nota: FINISHED_UNCONFIRMED ya no está permitido según regla estricta
        # Solo FINISHED_CONFIRMED puede crear órdenes
        
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
        
        # Heurística 1: Evento con final reciente (desde ConfigService)
        sports_old_event_minutes = config_service.get("sports_old_event_minutes", 10)
        sports_old_event_size_factor = config_service.get("sports_old_event_size_factor", 0.7)
        
        if event_state.event_finished_at:
            time_since_finished = datetime.utcnow() - event_state.event_finished_at
            if time_since_finished > timedelta(minutes=sports_old_event_minutes):
                # Entradas menos agresivas
                size = size * sports_old_event_size_factor
                # safety_tick ya se ajusta en _calculate_target_price
        
        # Heurística 2: Múltiples fuentes coinciden (desde ConfigService)
        sports_multi_source_threshold = config_service.get("sports_multi_source_threshold", 3)
        sports_multi_source_size_factor = config_service.get("sports_multi_source_size_factor", 1.1)
        
        sources_finished = [
            source for source, status in event_state.sources_state.items()
            if status == "FINISHED"
        ]
        if len(sources_finished) >= sports_multi_source_threshold:
            # Permitir entradas más agresivas
            size = size * sports_multi_source_size_factor
        
        return size
    
    def _get_orderbook_liquidity(self, market_id: UUID, target_price: float) -> float:
        """
        Obtiene liquidez disponible en orderbook al precio objetivo.
        
        TODO: Implementar parsing real del orderbook
        """
        # Obtener liquidez por defecto desde ConfigService
        default_liquidity = config_service.get("default_orderbook_liquidity", 10000.0)
        
        if market_id in state.markets:
            market_state = state.markets[market_id]
            if market_state.orderbook_snapshot:
                # Parse orderbook para encontrar liquidez al target_price
                # Por ahora, retornar estimación
                return market_state.orderbook_snapshot.get("liquidity_at_price", {}).get(
                    str(target_price), default_liquidity
                )
        
        # Default liquidity estimate
        return default_liquidity
    
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
    
    def _create_event_state_from_internal(self, event_id: UUID) -> Optional[EventState]:
        """
        Crea EventState desde el estado interno.
        
        Convierte el EventState interno a la estructura esperada.
        
        ⚠️ IMPORTANTE: Ahora recibe event_id, no market_id.
        """
        if event_id not in state.events:
            return None
        
        internal_state = state.events[event_id]
        
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
        
        # ⚠️ IMPORTANTE: Iterar por Events, no Markets
        # Strategy ahora opera sobre Events (instancias tradeables), no Markets (plantillas)
        for event_id, event_internal_state in state.events.items():
            # Obtener market_id desde el Event para cálculos de exposición
            market_id = event_internal_state.market_id
            if not market_id:
                continue
            
            # Crear MarketState desde estado interno (necesario para precios)
            market_state = self._create_market_state_from_internal(market_id)
            if not market_state:
                continue
            
            # Crear EventState desde estado interno
            event_state = self._create_event_state_from_internal(event_id)
            if not event_state:
                no_entry_reasons.append(NoEntryReason(
                    event_id=event_id,
                    reason="no_event_state",
                    details={"message": "Event state not available", "market_id": str(market_id)},
                    trace_id=trace_id
                ))
                continue
            
            # Verificar condiciones de activación
            should_enter, reason, details = self._check_activation_conditions(
                market_id, market_state, event_state, trace_id
            )
            
            if not should_enter:
                no_entry_reasons.append(NoEntryReason(
                    event_id=event_id,
                    reason=reason,
                    details={**details, "market_id": str(market_id)},
                    trace_id=trace_id
                ))
                
                # Log decision trace
                decision_trace_service.log_decision(
                    trace_id=trace_id,
                    component="strategy",
                    decision_stage="STRATEGY",
                    decision_type="reject",
                    decision="REJECTED",
                    input_data={
                        "event_id": str(event_id),
                        "market_id": str(market_id),
                        "best_ask": market_state.best_ask,
                        "best_bid": market_state.best_bid,
                        "spread": market_state.spread,
                        "event_state": event_state.event_status,
                        "event_confidence": event_state.confidence_score,
                        "latency_status": latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
                    },
                    reason=reason,
                    market_id=market_id,  # Mantener para compatibilidad con decision_trace
                    latency_ms=None,
                    confidence_score=event_state.confidence_score,
                    metadata=details
                )
                
                logger.debug(
                    f"Event {event_id} (Market {market_id}): No entry - {reason}",
                    extra={"event_id": str(event_id), "market_id": str(market_id), "reason": reason, "details": details, "trace_id": str(trace_id)}
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
                    event_id=event_id,
                    reason="target_price_too_low",
                    details={
                        "calculated_price": target_price,
                        "min_price_required": config.min_entry_price,
                        "market_id": str(market_id)
                    },
                    trace_id=trace_id
                ))
                continue
            
            # Obtener liquidez del orderbook
            liquidity = self._get_orderbook_liquidity(market_id, target_price)
            
            if liquidity < config.min_liquidity_required:
                no_entry_reasons.append(NoEntryReason(
                    event_id=event_id,
                    reason="insufficient_liquidity",
                    details={
                        "available_liquidity": liquidity,
                        "min_required": config.min_liquidity_required,
                        "market_id": str(market_id)
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
            
            # ⚠️ IMPORTANTE: Determinar outcome (YES/NO/UP/DOWN)
            # Por ahora, usar "YES" como default. En el futuro, debería venir del Event o Market.
            # TODO: Obtener outcomes desde Event.polymarket_payload o Market.polymarket_payload
            outcome = "YES"  # Default, debería venir del Event/Market
            
            # Solo crear intent si size > 0
            if size > 0:
                intent = OrderIntent(
                    event_id=event_id,
                    outcome=outcome,
                    side="BUY",
                    price=target_price,
                    size=size,
                    reason="conditions_met",
                    metadata={
                        "market_id": str(market_id),  # Incluir para cálculos de exposición
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
                
                # Log decision trace para OrderIntent creado
                decision_trace_service.log_decision(
                    trace_id=trace_id,
                    component="strategy",
                    decision_stage="STRATEGY",
                    decision_type="entry",
                    decision="APPROVED",
                    input_data={
                        "event_id": str(event_id),
                        "market_id": str(market_id),
                        "best_ask": market_state.best_ask,
                        "best_bid": market_state.best_bid,
                        "spread": market_state.spread,
                        "event_state": event_state.event_status,
                        "event_confidence": event_state.confidence_score,
                        "current_exposure": state.exposures.get(market_id, type('obj', (object,), {'notional': 0.0})()).notional if market_id in state.exposures else 0.0,
                        "exposure_limit": config.max_exposure_per_market,
                        "latency_status": latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
                        "liquidity": liquidity,
                    },
                    output_data={
                        "order_intent": {
                            "price": target_price,
                            "size": size,
                            "side": "BUY",
                            "outcome": outcome,
                        }
                    },
                    reason="conditions_met",
                    market_id=market_id,  # Mantener para compatibilidad con decision_trace
                    latency_ms=None,
                    confidence_score=event_state.confidence_score,
                )
                
                logger.info(
                    f"Created order intent for event {event_id} (market {market_id})",
                    extra={
                        "event_id": str(event_id),
                        "market_id": str(market_id),
                        "outcome": outcome,
                        "price": target_price,
                        "size": size,
                        "trace_id": str(trace_id)
                    }
                )
            else:
                no_entry_reasons.append(NoEntryReason(
                    event_id=event_id,
                    reason="size_too_small",
                    details={
                        "calculated_size": size,
                        "min_size": 0.0,
                        "market_id": str(market_id)
                    },
                    trace_id=trace_id
                ))
        
        self._last_intents = intents
        self._last_no_entry_reasons = no_entry_reasons
        
        return intents

