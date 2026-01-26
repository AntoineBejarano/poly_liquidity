"""
Risk Engine - Control de exposiciones, entradas y seguridad operacional.

Refactorizado según especificación en docs/services/risk_engine.md
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from app.core.state import state
from app.core.config_service import config_service
from app.core.strategy.models import OrderIntent
from app.core.decision_trace import decision_trace_service
from app.core.latency_monitor import latency_monitor, LatencyStatus
from app.core.runtime_supervisor import RuntimeMode
from app.core.risk_engine.models import (
    ApprovedOrderIntent, RejectedOrderIntent, ExposureState, RuntimeState, RiskConfig
)
from app.database import SessionLocal
from app.models.exposure import Exposure

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Risk Engine service.
    
    Responsabilidades:
    - Validar Order Intents según reglas de riesgo
    - Ajustar tamaños cuando es necesario
    - Mantener estado de exposición
    - Implementar fail-safes de emergencia
    - Bloquear órdenes peligrosas
    """
    
    def __init__(self):
        """Inicializa el Risk Engine."""
        # #region agent log
        import json, os
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"risk_engine.py:37","message":"RiskEngine.__init__ ENTRY","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("RiskEngine.__init__ - Iniciando inicialización...")
        self._blocked_markets: set[UUID] = set()  # Mercados bloqueados por fail-safes
        self._price_history: Dict[UUID, List[Tuple[float, datetime]]] = {}  # Historial de precios
        # #region agent log
        with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"risk_engine.py:41","message":"RiskEngine.__init__ EXIT","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
        # #endregion
        logger.info("RiskEngine.__init__ - Inicialización completada")
    
    def _get_config(self) -> RiskConfig:
        """
        Obtiene la configuración de riesgo desde ConfigService.
        
        Usa hot reload para obtener siempre la configuración más reciente.
        """
        # Siempre obtener desde ConfigService para hot reload
        return config_service.get_risk_engine_config()
    
    def _calculate_exposure(self, size: float, price: float) -> float:
        """Calcula exposición: size * price."""
        return size * price
    
    def _calculate_global_exposure(self) -> float:
        """Calcula exposición global total."""
        total = 0.0
        for exposure_state in state.exposures.values():
            total += exposure_state.notional
        return total
    
    def _get_market_id_from_intent(self, intent: OrderIntent) -> Optional[UUID]:
        """
        Obtiene market_id desde el OrderIntent.
        
        ⚠️ IMPORTANTE: OrderIntent ahora usa event_id, pero necesitamos market_id para cálculos de exposición.
        El market_id se obtiene desde:
        1. intent.metadata.get("market_id") (si está disponible)
        2. state.events[intent.event_id].market_id (desde el Event)
        """
        # Intentar desde metadata primero
        if "market_id" in intent.metadata:
            try:
                market_id_str = intent.metadata.get("market_id")
                if isinstance(market_id_str, str):
                    return UUID(market_id_str)
            except (ValueError, TypeError):
                pass
        
        # Obtener desde Event
        if intent.event_id in state.events:
            event_state = state.events[intent.event_id]
            return event_state.market_id
        
        return None
    
    def _get_active_markets(self, new_market_id: Optional[UUID] = None) -> set[UUID]:
        """Obtiene conjunto de mercados activos."""
        active_markets = set()
        
        # Mercados con posiciones
        for pos_id, pos in state.positions.items():
            if pos and hasattr(pos, 'market_id') and pos.market_id:
                active_markets.add(pos.market_id)
        
        # Mercados con órdenes pendientes
        for order_id, order_state in state.orders.items():
            if order_state and hasattr(order_state, 'status') and order_state.status in ("NEW", "PARTIALLY_FILLED"):
                if hasattr(order_state, 'market_id') and order_state.market_id:
                    active_markets.add(order_state.market_id)
        
        # Si es un nuevo mercado, agregarlo al conteo
        if new_market_id:
            active_markets.add(new_market_id)
        
        return active_markets
    
    def _check_rule_1_market_exposure(self, intent: OrderIntent) -> Tuple[bool, str, Optional[float]]:
        """
        Regla 1: Exposición Máxima por Mercado.
        
        Returns: (is_valid, reason_if_invalid, max_allowed_size)
        """
        config = self._get_config()
        
        # Obtener market_id desde el Event
        market_id = self._get_market_id_from_intent(intent)
        if not market_id:
            return (False, "market_id_not_available", None)
        
        # Calcular exposición actual del mercado
        current_market_exposure = 0.0
        if market_id in state.exposures:
            current_market_exposure = state.exposures[market_id].notional
        
        # Calcular nueva exposición para este mercado
        new_exposure = current_market_exposure + self._calculate_exposure(intent.size, intent.price)
        
        # Validar
        if new_exposure > config.max_market_exposure:
            # Calcular tamaño máximo permitido
            remaining = config.max_market_exposure - current_market_exposure
            max_allowed_size = remaining / intent.price if intent.price > 0 else 0.0
            
            return (False, "exceeds_market_exposure_limit", max_allowed_size)
        
        return (True, "", None)
    
    def _check_rule_2_global_exposure(self, intent: OrderIntent) -> Tuple[bool, str, Optional[float]]:
        """
        Regla 2: Exposición Global Máxima.
        
        Returns: (is_valid, reason_if_invalid, max_allowed_size)
        """
        config = self._get_config()
        
        # Calcular nueva exposición global
        current_global = self._calculate_global_exposure()
        new_exposure = current_global + self._calculate_exposure(intent.size, intent.price)
        
        # Validar
        if new_exposure > config.max_global_exposure:
            # Calcular tamaño máximo permitido
            remaining = config.max_global_exposure - current_global
            max_allowed_size = remaining / intent.price if intent.price > 0 else 0.0
            
            return (False, "exceeds_global_exposure_limit", max_allowed_size)
        
        return (True, "", None)
    
    def _check_rule_3_max_markets_active(self, intent: OrderIntent) -> Tuple[bool, str]:
        """
        Regla 3: Máximo de Mercados Activos.
        
        Returns: (is_valid, reason_if_invalid)
        """
        config = self._get_config()
        
        # Obtener market_id desde el Event
        market_id = self._get_market_id_from_intent(intent)
        if not market_id:
            return (False, "market_id_not_available")
        
        active_markets = self._get_active_markets(market_id)
        
        # Validar
        if len(active_markets) > config.max_markets_active:
            return (False, "exceeds_max_markets_active")
        
        return (True, "")
    
    def _check_rule_4_max_order_size(self, intent: OrderIntent) -> Tuple[bool, Optional[float]]:
        """
        Regla 4: Tamaño Máximo por Orden.
        
        El Risk Engine reduce, no rechaza (a menos que sea demasiado grande).
        
        Returns: (is_valid, adjusted_size_if_needed)
        """
        config = self._get_config()
        
        if intent.size > config.max_order_size:
            # Reducir tamaño
            return (True, config.max_order_size)
        
        return (True, None)
    
    def _check_rule_5_latency_control(self, intent: OrderIntent) -> Tuple[bool, str, Optional[float]]:
        """
        Regla 5: Control de Latencia.
        
        Returns: (is_valid, reason_if_invalid, size_factor_if_yellow)
        """
        config = self._get_config()
        
        # Obtener runtime mode
        try:
            import app.main as main_module
            runtime_supervisor = main_module.runtime_supervisor
            runtime_mode = runtime_supervisor.get_mode()
        except (AttributeError, ImportError):
            runtime_mode = RuntimeMode.GREEN
        
        # Obtener latency status
        latency_status = latency_monitor.get_status()
        
        # RED: Rechazar todas
        if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED:
            return (False, "latency_too_high", None)
        
        # YELLOW: Reducir tamaño
        if (runtime_mode == RuntimeMode.YELLOW or latency_status == LatencyStatus.YELLOW) and config.reduce_size_in_yellow:
            return (True, "", config.yellow_size_factor)
        
        return (True, "", None)
    
    def _check_rule_6_price_swings(self, intent: OrderIntent) -> Tuple[bool, str]:
        """
        Regla 6: Swings Abruptos del Mercado (Protección Anti-Manipulación).
        
        Returns: (is_valid, reason_if_invalid)
        """
        config = self._get_config()
        
        # Obtener market_id desde el Event
        market_id = self._get_market_id_from_intent(intent)
        if not market_id:
            return (False, "market_id_not_available")
        
        # Obtener historial de precios para este mercado
        if market_id not in self._price_history:
            self._price_history[market_id] = []
        
        price_history = self._price_history[market_id]
        now = datetime.utcnow()
        
        # Agregar precio actual
        price_history.append((intent.price, now))
        
        # Limpiar historial antiguo (desde ConfigService)
        price_history_window_seconds = config_service.get("price_history_window_seconds", 60)
        cutoff = now - timedelta(seconds=price_history_window_seconds)
        price_history[:] = [(p, t) for p, t in price_history if t > cutoff]
        
        # Verificar swings si hay suficiente historial
        if len(price_history) >= 2:
            previous_price, previous_time = price_history[-2]
            current_price = intent.price
            
            price_change_pct = abs(current_price - previous_price) / previous_price if previous_price > 0 else 0.0
            time_diff = (now - previous_time).total_seconds()
            
            # Detectar swing abrupto
            if price_change_pct > config.max_price_swing_pct and time_diff < config.max_swing_time_seconds:
                return (False, "suspicious_price_movement")
        
        # Verificar spread (si está en metadata)
        if "spread" in intent.metadata:
            spread = intent.metadata.get("spread", 0.0)
            if spread < config.min_realistic_spread:
                return (False, "suspicious_spread")
        
        return (True, "")
    
    def _check_rule_7_event_state(self, intent: OrderIntent) -> Tuple[bool, str]:
        """
        Regla 7: Validación del Estado del Evento.
        
        Returns: (is_valid, reason_if_invalid)
        """
        # ⚠️ IMPORTANTE: Ahora usamos event_id directamente
        if intent.event_id not in state.events:
            return (False, "event_state_not_available")
        
        event_state = state.events[intent.event_id]
        
        # Validar estado - Regla estricta: SOLO FINISHED_CONFIRMED permitido
        # El sistema SOLO puede crear órdenes cuando event_state == FINISHED_CONFIRMED
        # determinado exclusivamente por el EventEngine con quorum de ≥2 checkers independientes
        if event_state.state != "FINISHED_CONFIRMED":
            return (False, "event_not_finished")
        
        return (True, "")
    
    def _check_rule_8_market_overrides(self, intent: OrderIntent) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Regla 8: Reglas Personalizadas por Mercado.
        
        Returns: (is_valid, reason_if_invalid, overrides_if_any)
        """
        # Por ahora, no hay overrides implementados
        # Esto puede extenderse en el futuro
        return (True, "", None)
    
    def _adjust_size(
        self,
        intent: OrderIntent,
        size_adjustments: List[Optional[float]],
        latency_factor: Optional[float]
    ) -> float:
        """
        Ajusta tamaño según múltiples restricciones.
        
        Según especificación en docs/services/risk_engine.md
        """
        config = self._get_config()
        
        # Calcular tamaños desde diferentes restricciones
        sizes = [intent.size]  # Tamaño original
        
        # Agregar ajustes válidos
        for adj in size_adjustments:
            if adj is not None and adj > 0:
                sizes.append(adj)
        
        # Obtener market_id desde el Event
        market_id = self._get_market_id_from_intent(intent)
        if not market_id:
            # Si no hay market_id, no podemos calcular exposición por mercado
            # Usar solo límites globales
            pass
        else:
            # Calcular exposición restante por mercado
            current_market_exposure = 0.0
            if market_id in state.exposures:
                current_market_exposure = state.exposures[market_id].notional
            
            remaining_market = config.max_market_exposure - current_market_exposure
            size_from_market = remaining_market / intent.price if intent.price > 0 else 0.0
            if size_from_market > 0:
                sizes.append(size_from_market)
        
        # Calcular exposición global restante
        current_global = self._calculate_global_exposure()
        remaining_global = config.max_global_exposure - current_global
        size_from_global = remaining_global / intent.price if intent.price > 0 else 0.0
        if size_from_global > 0:
            sizes.append(size_from_global)
        
        # Aplicar factor de latencia si es YELLOW
        if latency_factor is not None:
            base_size = min(sizes) if sizes else intent.size
            sizes.append(base_size * latency_factor)
        
        # Tomar el mínimo
        final_size = min(sizes) if sizes else intent.size
        
        # Validar tamaño mínimo
        if final_size < config.min_order_size:
            return 0.0  # Muy pequeño, rechazar
        
        return final_size
    
    def _check_risk_rules(self, intent: OrderIntent) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifica todas las reglas de riesgo.
        
        Returns: (is_valid, reason_if_invalid, adjustments_dict)
        """
        adjustments: Dict[str, Any] = {}
        size_adjustments: List[Optional[float]] = []
        
        # Regla 1: Exposición por mercado
        is_valid, reason, max_size = self._check_rule_1_market_exposure(intent)
        if not is_valid:
            # Si podemos ajustar tamaño, intentar
            if max_size and max_size > 0:
                size_adjustments.append(max_size)
                adjustments["market_exposure_limit"] = max_size
            else:
                return (False, reason, adjustments)
        
        # Regla 2: Exposición global
        is_valid, reason, max_size = self._check_rule_2_global_exposure(intent)
        if not is_valid:
            if max_size and max_size > 0:
                size_adjustments.append(max_size)
                adjustments["global_exposure_limit"] = max_size
            else:
                return (False, reason, adjustments)
        
        # Regla 3: Máximo de mercados activos
        is_valid, reason = self._check_rule_3_max_markets_active(intent)
        if not is_valid:
            return (False, reason, adjustments)
        
        # Regla 4: Tamaño máximo por orden
        is_valid, adjusted_size = self._check_rule_4_max_order_size(intent)
        if adjusted_size is not None:
            size_adjustments.append(adjusted_size)
            adjustments["size_limit"] = adjusted_size
        
        # Regla 5: Control de latencia
        is_valid, reason, latency_factor = self._check_rule_5_latency_control(intent)
        if not is_valid:
            return (False, reason, adjustments)
        if latency_factor is not None:
            adjustments["latency_factor"] = latency_factor
        
        # Regla 6: Swings de precio
        is_valid, reason = self._check_rule_6_price_swings(intent)
        if not is_valid:
            return (False, reason, adjustments)
        
        # Regla 7: Estado del evento
        is_valid, reason = self._check_rule_7_event_state(intent)
        if not is_valid:
            return (False, reason, adjustments)
        
        # Regla 8: Overrides por mercado
        is_valid, reason, overrides = self._check_rule_8_market_overrides(intent)
        if not is_valid:
            return (False, reason, adjustments)
        if overrides:
            adjustments["market_overrides"] = overrides
        
        # Ajustar tamaño
        final_size = self._adjust_size(intent, size_adjustments, latency_factor)
        if final_size == 0.0:
            return (False, "size_too_small_after_adjustments", adjustments)
        
        adjustments["final_size"] = final_size
        adjustments["original_size"] = intent.size
        
        return (True, "", adjustments)
    
    def _update_exposure_state(self, intent: OrderIntent, final_size: float):
        """Actualiza estado de exposición después de aprobación."""
        # Obtener market_id desde el Event
        market_id = self._get_market_id_from_intent(intent)
        if not market_id:
            logger.warning(f"Cannot update exposure state: market_id not available for event {intent.event_id}")
            return
        
        new_exposure = self._calculate_exposure(final_size, intent.price)
        
        if market_id not in state.exposures:
            from app.core.state import ExposureState as InternalExposureState
            state.exposures[market_id] = InternalExposureState()
            state.exposures[market_id].market_id = market_id
        
        exposure_state = state.exposures[market_id]
        exposure_state.notional += new_exposure
        exposure_state.max_allowed = self._get_config().max_market_exposure
        exposure_state.breached = exposure_state.notional > exposure_state.max_allowed
        exposure_state.updated_at = datetime.utcnow()
        
        # Persistir a DB
        db = SessionLocal()
        try:
            db_exposure = db.query(Exposure).filter(Exposure.market_id == market_id).first()
            if not db_exposure:
                db_exposure = Exposure(
                    id=uuid4(),
                    market_id=market_id,
                    notional=exposure_state.notional,
                    max_allowed=exposure_state.max_allowed,
                    breached=exposure_state.breached,
                    timestamp=datetime.utcnow(),
                )
                db.add(db_exposure)
            else:
                db_exposure.notional = exposure_state.notional
                db_exposure.max_allowed = exposure_state.max_allowed
                db_exposure.breached = exposure_state.breached
                db_exposure.timestamp = datetime.utcnow()
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating exposure in DB: {e}")
        finally:
            db.close()
    
    def _trigger_fail_safe_latency_red(self):
        """Fail-Safe 1: Latencia Roja (Autopausa)."""
        config = self._get_config()
        
        logger.error(
            "Fail-safe triggered: Latency RED",
            extra={
                "component": "risk_engine",
                "action": "trigger_fail_safe",
                "reason": "latency_red"
            }
        )
        
        # Bloquear nuevas órdenes (ya se hace en tick)
        # Cancelar órdenes pendientes si está configurado
        if config.cancel_on_red:
            # TODO: Implementar cancelación de órdenes pendientes
            logger.warning("Should cancel pending orders (not implemented yet)")
    
    def _trigger_fail_safe_exposure_breach(self, market_id: UUID, exposure: float):
        """Fail-Safe 2: Exposición Desproporcionada."""
        self._blocked_markets.add(market_id)
        
        logger.error(
            f"Fail-safe triggered: Exposure breach for market {market_id}",
            extra={
                "component": "risk_engine",
                "action": "trigger_fail_safe",
                "reason": "exposure_breach",
                "market_id": str(market_id),
                "exposure": exposure
            }
        )
    
    def _trigger_fail_safe_watch_engine_misaligned(self, event_id: str):
        """Fail-Safe 3: Watch Engine Desalineado."""
        logger.error(
            f"Fail-safe triggered: Watch Engine misaligned for event {event_id}",
            extra={
                "component": "risk_engine",
                "action": "trigger_fail_safe",
                "reason": "watch_engine_misaligned",
                "event_id": event_id
            }
        )
    
    async def tick(self, intents: List[OrderIntent]) -> List[ApprovedOrderIntent]:
        """
        Aplica límites de riesgo a Order Intents.
        
        Returns:
            Lista de ApprovedOrderIntent que pasaron todas las reglas de riesgo.
        """
        approved: List[ApprovedOrderIntent] = []
        trace_id = uuid4()
        
        # Obtener runtime mode
        try:
            import app.main as main_module
            runtime_supervisor = main_module.runtime_supervisor
            runtime_mode = runtime_supervisor.get_mode()
        except (AttributeError, ImportError):
            runtime_mode = RuntimeMode.GREEN
        
        # Obtener latency status
        latency_status = latency_monitor.get_status()
        
        # Fail-Safe 1: RED mode/status - rechazar todas las órdenes
        if runtime_mode == RuntimeMode.RED or latency_status == LatencyStatus.RED:
            self._trigger_fail_safe_latency_red()
            logger.warning(
                "Runtime mode/latency RED: Rejecting all new order intents (fail-safe)",
                extra={
                    "component": "risk_engine",
                    "runtime_mode": runtime_mode.value if hasattr(runtime_mode, 'value') else str(runtime_mode),
                    "latency_status": latency_status.value if hasattr(latency_status, 'value') else str(latency_status),
                    "trace_id": str(trace_id)
                }
            )
            return approved
        
        # Procesar cada intent
        for intent in intents:
            # Obtener market_id desde el Event
            market_id = self._get_market_id_from_intent(intent)
            
            # Verificar si el mercado está bloqueado
            if market_id and market_id in self._blocked_markets:
                logger.warning(
                    f"Order intent rejected: Market {market_id} is blocked",
                    extra={
                        "component": "risk_engine",
                        "event_id": str(intent.event_id),
                        "market_id": str(market_id) if market_id else None,
                        "reason": "market_blocked",
                        "trace_id": str(trace_id)
                    }
                )
                continue
            
            # Verificar reglas de riesgo
            is_valid, reason, adjustments = self._check_risk_rules(intent)
            
            if not is_valid:
                logger.warning(
                    f"Order intent rejected: {reason}",
                    extra={
                        "component": "risk_engine",
                        "event_id": str(intent.event_id),
                        "market_id": str(market_id) if market_id else None,
                        "reason": reason,
                        "adjustments": adjustments,
                        "trace_id": str(trace_id)
                    }
                )
                continue
            
            # Obtener tamaño final
            final_size = adjustments.get("final_size", intent.size)
            
            # Obtener market_id para metadata
            market_id = self._get_market_id_from_intent(intent)
            
            # Crear approved intent
            approved_intent = ApprovedOrderIntent(
                event_id=intent.event_id,
                outcome=intent.outcome,
                side=intent.side,
                price=intent.price,
                size=final_size,
                original_size=intent.size,
                adjustments={**adjustments, "market_id": str(market_id) if market_id else None},
                trace_id=intent.trace_id or trace_id
            )
            approved.append(approved_intent)
            
            # Actualizar estado de exposición
            self._update_exposure_state(intent, final_size)
            
            # Log decision trace para aprobación
            decision_trace_service.log_decision(
                trace_id=approved_intent.trace_id,
                component="risk",
                decision_stage="RISK",
                decision_type="entry" if final_size == intent.size else "adjust",
                decision="APPROVED" if final_size == intent.size else "ADJUSTED",
                input_data={
                    "event_id": str(intent.event_id),
                    "market_id": str(market_id) if market_id else None,
                    "price": intent.price,
                    "size": intent.size,
                    "current_market_exposure": state.exposures.get(market_id, type('obj', (object,), {'notional': 0.0})()).notional if market_id and market_id in state.exposures else 0.0,
                    "max_market_exposure": self._get_config().max_market_exposure,
                    "current_global_exposure": self._calculate_global_exposure(),
                    "max_global_exposure": self._get_config().max_global_exposure,
                    "active_markets": len(self._get_active_markets()),
                },
                output_data={
                    "approved_intent": {
                        "price": approved_intent.price,
                        "size": final_size,
                        "original_size": intent.size,
                        "outcome": approved_intent.outcome,
                    }
                },
                reason="all_limits_respected" if final_size == intent.size else "size_adjusted",
                market_id=market_id,  # Mantener para compatibilidad con decision_trace
                metadata=adjustments
            )
            
            logger.info(
                f"Order intent approved for event {intent.event_id} (market {market_id})",
                extra={
                    "component": "risk_engine",
                    "action": "approved",
                    "event_id": str(intent.event_id),
                    "market_id": str(market_id) if market_id else None,
                    "outcome": approved_intent.outcome,
                    "size": final_size,
                    "original_size": intent.size,
                    "adjustments": adjustments,
                    "trace_id": str(approved_intent.trace_id)
                }
            )
        
        return approved

