"""
Execution Coordinator Node - Coordina la ejecución de un ExecutionPlan.

Este nodo es responsable de:
- Obtener el plan de la DB con lock (SELECT FOR UPDATE)
- Validar invariantes
- Cambiar estado a EXECUTING (dentro de transacción)
- Ejecutar legs según modo (sequential, parallel, atomic)
- Manejar partial fills, retries, y compensación
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from app.core.strategy_engine.nodes.base import GraphNode, ExecutionResult, FailureResult
from app.models.execution_plan import ExecutionPlan
from app.core.strategy_engine.invariants import (
    validate_plan_immutability,
    validate_plan_state_transition,
    validate_plan_not_expired
)
from app.core.strategy_engine.risk_validator import RiskValidator
from app.core.strategy.models import OrderIntent

logger = logging.getLogger(__name__)


class ExecutionCoordinatorNode(GraphNode):
    """
    Nodo que coordina la ejecución de un ExecutionPlan.
    
    Este nodo es el corazón del Execution Graph.
    Maneja la ejecución de legs según el modo especificado.
    """
    
    async def execute(self) -> ExecutionResult:
        """
        Ejecuta un ExecutionPlan.
        
        Config:
            plan_id: str | UUID - ID del plan a ejecutar
            execution_mode: str - Modo de ejecución: "sequential" | "parallel" | "atomic"
            retry_config: dict - Configuración de reintentos (opcional)
            compensation_enabled: bool - Si se habilita compensación (default: True)
        
        Requiere:
            - db en context
            - execution_engine en context (opcional, para ejecutar órdenes)
        """
        plan_id = self.config.get("plan_id")
        execution_mode = self.config.get("execution_mode", "sequential")
        retry_config = self.config.get("retry_config", {})
        compensation_enabled = self.config.get("compensation_enabled", True)
        
        if not plan_id:
            return FailureResult("plan_id is required")
        
        # Resolver template si es necesario
        try:
            plan_id = self._resolve_template(plan_id)
        except ValueError as e:
            return FailureResult(f"plan_id could not be resolved: {str(e)}")
        
        # Convertir a UUID si es string
        if isinstance(plan_id, str):
            try:
                plan_id = UUID(plan_id)
            except ValueError:
                return FailureResult(f"Invalid plan_id format: {plan_id}")
        
        # CRÍTICO: Obtener plan de DB con lock (SELECT FOR UPDATE)
        # Esto previene race conditions cuando múltiples Execution Graphs
        # intentan ejecutar el mismo plan simultáneamente
        try:
            plan = self.context.db.query(ExecutionPlan).filter(
                ExecutionPlan.id == plan_id
            ).with_for_update().first()
            
            if not plan:
                return FailureResult(f"ExecutionPlan with ID {plan_id} not found")
            
            # Validar invariantes
            validate_plan_not_expired(plan)
            validate_plan_immutability(plan)
            
            # Validar risk_config del plan
            risk_validator = RiskValidator(plan)
            is_valid, error_msg = risk_validator.validate_plan_risk_config()
            if not is_valid:
                return FailureResult(f"Invalid risk_config: {error_msg}")
            
            # Validar transición de estado
            if plan.status != "PLAN_BUILT" and plan.status != "EXECUTING":
                # Si ya está en otro estado, no podemos ejecutarlo
                return FailureResult(
                    f"Cannot execute plan in status {plan.status}. "
                    f"Expected PLAN_BUILT or EXECUTING"
                )
            
            # Cambiar estado a EXECUTING (dentro de la transacción)
            if plan.status == "PLAN_BUILT":
                validate_plan_state_transition(plan.status, "EXECUTING")
                plan.status = "EXECUTING"
                self.context.db.flush()  # Flush para asegurar que el cambio se persiste
            
            # Crear risk_validator para usar durante la ejecución
            risk_validator = RiskValidator(plan)
            
            # Ejecutar legs según modo
            if execution_mode == "sequential":
                result = await self._execute_sequential(plan, retry_config, risk_validator)
            elif execution_mode == "parallel":
                result = await self._execute_parallel(plan, retry_config, risk_validator)
            elif execution_mode == "atomic":
                result = await self._execute_atomic(plan, retry_config, compensation_enabled, risk_validator)
            else:
                return FailureResult(f"Unknown execution_mode: {execution_mode}")
            
            # Actualizar estado del plan según resultado
            if result.get("all_completed"):
                validate_plan_state_transition(plan.status, "COMPLETED")
                plan.status = "COMPLETED"
            elif result.get("has_failures") and execution_mode == "atomic":
                # En modo atomic, si hay fallos, compensar y marcar como FAILED
                if compensation_enabled:
                    # TODO: Llamar a compensate_plan node
                    pass
                validate_plan_state_transition(plan.status, "FAILED")
                plan.status = "FAILED"
            elif result.get("has_partial_fills"):
                # Hay partial fills, el plan puede continuar ejecutándose
                # No cambiar estado, dejar en EXECUTING
                pass
            
            self.context.db.flush()
            
            return ExecutionResult(
                plan_id=plan_id,
                legs_status=result,
                success=result.get("all_completed", False),
                error=result.get("error")
            )
            
        except ValueError as e:
            # Error de validación de invariantes
            self.context.db.rollback()
            return FailureResult(f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error executing plan {plan_id}: {e}", exc_info=True)
            self.context.db.rollback()
            return FailureResult(f"Execution error: {str(e)}")
    
    async def _execute_sequential(self, plan: ExecutionPlan, retry_config: Dict[str, Any], risk_validator: RiskValidator) -> Dict[str, Any]:
        """
        Ejecuta legs secuencialmente (uno después del otro).
        
        Si un leg falla, se puede abortar según la política de retry.
        """
        legs = plan.legs or []
        results = {}
        all_completed = True
        has_failures = False
        
        for leg in legs:
            leg_id = leg.get("leg_id", "unknown")
            try:
                # Validar precio antes de ejecutar (si abort_on_price_move está activo)
                if risk_validator.should_abort_on_price_move():
                    # Obtener precio actual del mercado
                    current_price = self._get_current_price(plan)
                    if current_price:
                        is_valid, error_msg = risk_validator.validate_price(leg, current_price)
                        if not is_valid:
                            logger.warning(f"Price validation failed for leg {leg_id}: {error_msg}")
                            results[leg_id] = {"success": False, "error": f"Price validation failed: {error_msg}"}
                            has_failures = True
                            all_completed = False
                            break
                
                result = await self._execute_leg(leg, plan, risk_validator)
                results[leg_id] = result
                
                if not result.get("success"):
                    has_failures = True
                    all_completed = False
                    # En sequential, si un leg falla, podemos abortar o continuar
                    # según la política (por ahora, abortamos)
                    break
            except Exception as e:
                logger.error(f"Error executing leg {leg_id}: {e}", exc_info=True)
                results[leg_id] = {"success": False, "error": str(e)}
                has_failures = True
                all_completed = False
                break
        
        return {
            "legs": results,
            "all_completed": all_completed,
            "has_failures": has_failures,
            "has_partial_fills": False  # Sequential no maneja partial fills por ahora
        }
    
    async def _execute_parallel(self, plan: ExecutionPlan, retry_config: Dict[str, Any], risk_validator: RiskValidator) -> Dict[str, Any]:
        """
        Ejecuta legs en paralelo (todos a la vez).
        
        Tolera fills en distintos tiempos.
        """
        legs = plan.legs or []
        import asyncio
        
        # Ejecutar todos los legs en paralelo
        tasks = [self._execute_leg(leg, plan, risk_validator) for leg in legs]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        all_completed = True
        has_failures = False
        has_partial_fills = False
        
        for i, leg in enumerate(legs):
            leg_id = leg.get("leg_id", f"leg_{i}")
            result = results_list[i]
            
            if isinstance(result, Exception):
                results[leg_id] = {"success": False, "error": str(result)}
                has_failures = True
                all_completed = False
            else:
                results[leg_id] = result
                if not result.get("success"):
                    has_failures = True
                    all_completed = False
                if result.get("partial_fill"):
                    has_partial_fills = True
        
        return {
            "legs": results,
            "all_completed": all_completed,
            "has_failures": has_failures,
            "has_partial_fills": has_partial_fills
        }
    
    async def _execute_atomic(self, plan: ExecutionPlan, retry_config: Dict[str, Any], compensation_enabled: bool, risk_validator: RiskValidator) -> Dict[str, Any]:
        """
        Ejecuta legs en modo atomic.
        
        Si no se completan todos los legs dentro del budget/TTL,
        se compensa según strategy y se marca FAILED.
        """
        legs = plan.legs or []
        results = {}
        all_completed = True
        has_failures = False
        has_partial_fills = False
        
        # Ejecutar todos los legs
        import asyncio
        tasks = [self._execute_leg(leg, plan, risk_validator) for leg in legs]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, leg in enumerate(legs):
            leg_id = leg.get("leg_id", f"leg_{i}")
            result = results_list[i]
            
            if isinstance(result, Exception):
                results[leg_id] = {"success": False, "error": str(result)}
                has_failures = True
                all_completed = False
            else:
                results[leg_id] = result
                if not result.get("success"):
                    has_failures = True
                    all_completed = False
                if result.get("partial_fill"):
                    has_partial_fills = True
        
        # En modo atomic, si hay fallos o partial fills, compensar
        if (has_failures or has_partial_fills) and compensation_enabled:
            # TODO: Llamar a compensate_plan node
            # Por ahora, solo marcamos que necesita compensación
            pass
        
        return {
            "legs": results,
            "all_completed": all_completed,
            "has_failures": has_failures,
            "has_partial_fills": has_partial_fills
        }
    
    async def _execute_leg(self, leg: Dict[str, Any], plan: ExecutionPlan, risk_validator: RiskValidator) -> Dict[str, Any]:
        """
        Ejecuta un leg individual del plan usando TradingPlatform.
        
        Usa la abstracción de plataforma para enviar la orden,
        permitiendo que el sistema sea multi-plataforma.
        """
        try:
            # Obtener trading_platform del contexto (preferido) o execution_engine (legacy)
            trading_platform = getattr(self.context, 'trading_platform', None)
            execution_engine = getattr(self.context, 'execution_engine', None)
            
            if not trading_platform and not execution_engine:
                # Si no hay plataforma disponible, simular ejecución exitosa
                # (en producción, esto debería fallar)
                logger.warning("No trading_platform or execution_engine available, simulating leg execution")
                return {
                    "success": True,
                    "leg_id": leg.get("leg_id"),
                    "order_id": None,
                    "partial_fill": False
                }
            
            # Obtener el evento para metadata adicional
            event = plan.event
            if not event:
                return {
                    "success": False,
                    "error": "Event not found for plan",
                    "leg_id": leg.get("leg_id")
                }
            
            # Validar precio antes de ejecutar
            current_price = self._get_current_price(plan)
            if current_price:
                is_valid, error_msg = risk_validator.validate_price(leg, current_price)
                if not is_valid:
                    return {
                        "success": False,
                        "error": error_msg,
                        "leg_id": leg.get("leg_id")
                    }
            
            # Validar liquidez antes de ejecutar
            available_liquidity = self._get_available_liquidity(plan, leg)
            if available_liquidity is not None:
                is_valid, error_msg = risk_validator.validate_liquidity(leg, available_liquidity)
                if not is_valid:
                    return {
                        "success": False,
                        "error": error_msg,
                        "leg_id": leg.get("leg_id")
                    }
            
            # Usar TradingPlatform si está disponible (nuevo método)
            if trading_platform:
                return await self._execute_leg_via_platform(leg, plan, trading_platform, event)
            else:
                # Fallback a execution_engine (legacy)
                return await self._execute_leg_via_engine(leg, plan, execution_engine, event)
            
        except Exception as e:
            logger.error(f"Error executing leg {leg.get('leg_id')}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "leg_id": leg.get("leg_id")
            }
    
    async def _execute_leg_via_platform(
        self,
        leg: Dict[str, Any],
        plan: ExecutionPlan,
        trading_platform,
        event
    ) -> Dict[str, Any]:
        """
        Ejecuta un leg usando TradingPlatform (nuevo método).
        
        Este es el método preferido que usa la abstracción de plataforma.
        """
        from app.core.strategy_engine.models import PlanLeg
        from app.core.execution_engine.platform_models import PlatformFeatureNotSupported
        
        try:
            # Convertir leg dict a PlanLeg Pydantic model
            plan_leg = PlanLeg(
                leg_id=leg.get("leg_id"),
                side=leg.get("side"),
                outcome=leg.get("outcome"),
                target_price=Decimal(str(leg.get("target_price"))),
                size=Decimal(str(leg.get("size"))),
                size_usdc=Decimal(str(leg.get("size_usdc", leg.get("size") * leg.get("target_price", 0)))),
                status=leg.get("status", "PENDING"),
                filled_size=Decimal(str(leg.get("filled_size", 0))),
                filled_size_usdc=Decimal(str(leg.get("filled_size_usdc", 0))),
                reason=leg.get("reason", "Execution Plan"),
                metadata={
                    **(leg.get("metadata", {})),
                    "event_id": str(event.id),  # Añadir event_id para obtener token_id
                    "market_id": str(event.market_id) if event.market_id else None
                }
            )
            
            # Enviar orden usando TradingPlatform
            order_result = await trading_platform.submit_order(
                leg=plan_leg,
                risk_config=plan.risk_config or {},
                trace_id=plan.trace_id
            )
            
            # Actualizar estado del leg en el plan (dentro de la transacción)
            # Nota: No modificamos el plan inmutable, solo actualizamos el estado del leg
            leg["status"] = "EXECUTING"
            leg["platform_order_id"] = order_result.platform_order_id
            
            logger.info(
                f"Leg {leg.get('leg_id')} submitted via {trading_platform.get_platform_name()}: {order_result.platform_order_id}",
                extra={
                    "component": "execution_coordinator",
                    "event": "leg_submitted",
                    "leg_id": leg.get("leg_id"),
                    "platform_order_id": order_result.platform_order_id,
                    "trace_id": str(plan.trace_id) if plan.trace_id else None
                }
            )
            
            return {
                "success": True,
                "leg_id": leg.get("leg_id"),
                "order_id": order_result.platform_order_id,
                "partial_fill": order_result.filled_size > 0,
                "filled_size": float(order_result.filled_size),
                "filled_size_usdc": float(order_result.filled_size_usdc),
                "average_price": float(order_result.average_price) if order_result.average_price else None
            }
            
        except PlatformFeatureNotSupported as e:
            logger.error(
                f"Platform feature not supported for leg {leg.get('leg_id')}: {e}",
                extra={
                    "component": "execution_coordinator",
                    "event": "platform_feature_not_supported",
                    "leg_id": leg.get("leg_id"),
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": f"Platform feature not supported: {str(e)}",
                "leg_id": leg.get("leg_id")
            }
        except Exception as e:
            logger.error(
                f"Error executing leg {leg.get('leg_id')} via platform: {e}",
                exc_info=True,
                extra={
                    "component": "execution_coordinator",
                    "event": "leg_execution_error",
                    "leg_id": leg.get("leg_id")
                }
            )
            raise
    
    async def _execute_leg_via_engine(
        self,
        leg: Dict[str, Any],
        plan: ExecutionPlan,
        execution_engine,
        event
    ) -> Dict[str, Any]:
        """
        Ejecuta un leg usando Execution Engine (método legacy).
        
        Este método se mantiene para compatibilidad hacia atrás.
        """
        from app.core.strategy.models import OrderIntent
        
        # Crear OrderIntent desde el leg
        intent = OrderIntent(
            market_id=event.market_id,
            side=leg.get("side"),
            price=Decimal(str(leg.get("target_price"))),
            size=Decimal(str(leg.get("size"))),
            outcome=leg.get("outcome"),
            reason=leg.get("reason", "Execution Plan"),
            trace_id=plan.trace_id
        )
        
        # Enviar al Execution Engine
        logger.info(f"Executing leg {leg.get('leg_id')} for plan {plan.id} via execution_engine (legacy)")
        
        # Por ahora, solo simulamos la ejecución
        # TODO: Implementar llamada real a execution_engine cuando esté disponible
        return {
            "success": True,
            "leg_id": leg.get("leg_id"),
            "order_id": None,  # TODO: Obtener order_id real del execution_engine
            "partial_fill": False,
            "filled_size": leg.get("size"),
            "filled_size_usdc": leg.get("size_usdc")
        }
    
    def _resolve_template(self, value: Any) -> Any:
        """Resuelve templates como {{plan.id}} usando valores del contexto."""
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # Template encontrado
            if "{{plan.id}}" in value or "{{plan_id}}" in value:
                # Buscar en el contexto
                plan_id = None
                if hasattr(self.context, 'plan_id'):
                    plan_id = self.context.plan_id
                elif hasattr(self.context, 'last_plan_id'):
                    plan_id = self.context.last_plan_id
                
                if plan_id:
                    value = value.replace("{{plan.id}}", str(plan_id))
                    value = value.replace("{{plan_id}}", str(plan_id))
                    # Si el valor completo era el template, retornar directamente
                    if value == "{{plan.id}}" or value == "{{plan_id}}":
                        return plan_id
                else:
                    raise ValueError(f"Template {value} could not be resolved: plan_id not in context")
            
            # Si quedan templates sin resolver, lanzar error
            if "{{" in value and "}}" in value:
                    raise ValueError(f"Unresolved template in value: {value}")
        
        return value
    
    def _get_current_price(self, plan: ExecutionPlan) -> Optional[Decimal]:
        """
        Obtiene el precio actual del mercado desde el State Cache.
        
        Returns:
            Precio actual o None si no está disponible
        """
        try:
            if not hasattr(self.context, 'state_cache') or not self.context.state_cache:
                return None
            
            state = self.context.state_cache.get_state(plan.event_id)
            if not state:
                return None
            
            market_state = state.get("market_state")
            if not market_state or not isinstance(market_state, dict):
                return None
            
            # Intentar obtener last_price o price
            price_val = market_state.get("last_price") or market_state.get("price")
            if price_val is not None:
                return Decimal(str(price_val))
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting current price: {e}")
            return None
    
    def _get_available_liquidity(self, plan: ExecutionPlan, leg: Dict[str, Any]) -> Optional[Decimal]:
        """
        Obtiene la liquidez disponible en el mercado desde el State Cache.
        
        Returns:
            Liquidez disponible o None si no está disponible
        """
        try:
            if not hasattr(self.context, 'state_cache') or not self.context.state_cache:
                return None
            
            state = self.context.state_cache.get_state(plan.event_id)
            if not state:
                return None
            
            market_state = state.get("market_state")
            if not market_state or not isinstance(market_state, dict):
                return None
            
            # Intentar obtener liquidity o available_liquidity
            liquidity_val = market_state.get("liquidity") or market_state.get("available_liquidity")
            if liquidity_val is not None:
                return Decimal(str(liquidity_val))
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting available liquidity: {e}")
            return None

