"""
Retry Leg Node - Reintenta la ejecución de un leg fallido.

Este nodo maneja reintentos con backoff exponencial.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult, FailureResult
from app.models.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class RetryLegNode(GraphNode):
    """
    Nodo que reintenta la ejecución de un leg fallido.
    
    Soporta backoff exponencial y límite de reintentos.
    """
    
    async def execute(self) -> SuccessResult:
        """
        Reintenta un leg fallido.
        
        Config:
            leg_id: str - ID del leg a reintentar
            plan_id: str | UUID - ID del plan que contiene el leg
            max_retries: int - Máximo número de reintentos (default: 3)
            retry_delay_ms: int - Delay inicial en milisegundos (default: 1000)
            backoff_multiplier: float - Multiplicador para backoff exponencial (default: 2.0)
        
        Requiere:
            - db en context
        """
        leg_id = self.config.get("leg_id")
        plan_id = self.config.get("plan_id")
        max_retries = self.config.get("max_retries", 3)
        retry_delay_ms = self.config.get("retry_delay_ms", 1000)
        backoff_multiplier = self.config.get("backoff_multiplier", 2.0)
        
        if not leg_id:
            return FailureResult("leg_id is required")
        
        if not plan_id:
            return FailureResult("plan_id is required")
        
        # Resolver templates
        try:
            leg_id = self._resolve_template(leg_id)
            plan_id = self._resolve_template(plan_id)
        except ValueError as e:
            return FailureResult(f"Template resolution error: {str(e)}")
        
        # Convertir plan_id a UUID si es string
        if isinstance(plan_id, str):
            try:
                plan_id = UUID(plan_id)
            except ValueError:
                return FailureResult(f"Invalid plan_id format: {plan_id}")
        
        # Obtener plan de DB
        try:
            plan = self.context.db.query(ExecutionPlan).filter(
                ExecutionPlan.id == plan_id
            ).first()
            
            if not plan:
                return FailureResult(f"ExecutionPlan with ID {plan_id} not found")
            
            # Buscar el leg en el plan
            legs = plan.legs or []
            leg = None
            for l in legs:
                if l.get("leg_id") == leg_id:
                    leg = l
                    break
            
            if not leg:
                return FailureResult(f"Leg {leg_id} not found in plan {plan_id}")
            
            # Verificar si el leg ya está completado
            if leg.get("status") == "FILLED":
                return SuccessResult()  # Ya está completado, no necesita reintento
            
            # Reintentar el leg
            delay_ms = retry_delay_ms
            for attempt in range(max_retries):
                try:
                    # Esperar antes del reintento (excepto en el primer intento)
                    if attempt > 0:
                        await asyncio.sleep(delay_ms / 1000.0)
                        delay_ms = int(delay_ms * backoff_multiplier)  # Backoff exponencial
                    
                    # Ejecutar el leg (usar la misma lógica que execution_coordinator)
                    result = await self._execute_leg(leg, plan)
                    
                    if result.get("success"):
                        # Actualizar estado del leg en el plan
                        leg["status"] = "FILLED"
                        leg["filled_size"] = result.get("filled_size", leg.get("size"))
                        leg["filled_size_usdc"] = result.get("filled_size_usdc", leg.get("size_usdc"))
                        self.context.db.flush()
                        return SuccessResult()
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} failed for leg {leg_id}: "
                        f"{result.get('error', 'Unknown error')}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error in retry attempt {attempt + 1} for leg {leg_id}: {e}", exc_info=True)
            
            # Todos los reintentos fallaron
            leg["status"] = "FAILED"
            self.context.db.flush()
            return FailureResult(
                f"Leg {leg_id} failed after {max_retries} retry attempts"
            )
            
        except Exception as e:
            logger.error(f"Error retrying leg {leg_id}: {e}", exc_info=True)
            return FailureResult(f"Error retrying leg: {str(e)}")
    
    async def _execute_leg(self, leg: Dict[str, Any], plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Ejecuta un leg individual usando trading_platform (misma lógica que execution_coordinator).
        """
        try:
            # Obtener trading_platform del contexto (preferido) o execution_engine (legacy)
            trading_platform = getattr(self.context, 'trading_platform', None)
            execution_engine = getattr(self.context, 'execution_engine', None)
            
            if not trading_platform and not execution_engine:
                logger.warning("No trading_platform or execution_engine available, simulating leg execution")
                return {
                    "success": True,
                    "leg_id": leg.get("leg_id"),
                    "order_id": None,
                    "partial_fill": False,
                    "filled_size": leg.get("size"),
                    "filled_size_usdc": leg.get("size_usdc")
                }
            
            # Obtener el evento para metadata adicional
            event = plan.event
            if not event:
                return {
                    "success": False,
                    "error": "Event not found for plan",
                    "leg_id": leg.get("leg_id")
                }
            
            # Usar trading_platform si está disponible (preferido)
            if trading_platform:
                return await self._execute_leg_via_platform(leg, plan, trading_platform, event)
            else:
                # Fallback a execution_engine (legacy) - simular por ahora
                logger.warning("Using execution_engine (legacy) for retry, simulating execution")
                return {
                    "success": True,
                    "leg_id": leg.get("leg_id"),
                    "order_id": None,
                    "partial_fill": False,
                    "filled_size": leg.get("size"),
                    "filled_size_usdc": leg.get("size_usdc")
                }
            
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
        Ejecuta un leg usando TradingPlatform (mismo método que execution_coordinator).
        """
        from app.core.strategy_engine.models import PlanLeg
        from app.core.execution_engine.platform_models import PlatformFeatureNotSupported
        from decimal import Decimal
        
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
                reason=leg.get("reason", "Retry Execution Plan"),
                metadata={
                    **(leg.get("metadata", {})),
                    "event_id": str(event.id),
                    "market_id": str(event.market_id) if event.market_id else None
                }
            )
            
            # Enviar orden usando TradingPlatform
            order_result = await trading_platform.submit_order(
                leg=plan_leg,
                risk_config=plan.risk_config or {},
                trace_id=plan.trace_id
            )
            
            logger.info(
                f"Leg {leg.get('leg_id')} retried via {trading_platform.get_platform_name()}: {order_result.platform_order_id}",
                extra={
                    "component": "retry_leg",
                    "event": "leg_retried",
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
            logger.error(f"Platform feature not supported for leg {leg.get('leg_id')}: {e}")
            return {
                "success": False,
                "error": f"Platform feature not supported: {str(e)}",
                "leg_id": leg.get("leg_id")
            }
        except Exception as e:
            logger.error(f"Error executing leg {leg.get('leg_id')} via platform: {e}", exc_info=True)
            raise
    
    def _resolve_template(self, value: Any) -> Any:
        """Resuelve templates usando valores del contexto."""
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # Buscar en el contexto
            if "{{leg_id}}" in value:
                leg_id = getattr(self.context, 'leg_id', None)
                if leg_id:
                    value = value.replace("{{leg_id}}", str(leg_id))
                    if value == "{{leg_id}}":
                        return leg_id
            
            if "{{plan.id}}" in value or "{{plan_id}}" in value:
                plan_id = None
                if hasattr(self.context, 'plan_id'):
                    plan_id = self.context.plan_id
                elif hasattr(self.context, 'last_plan_id'):
                    plan_id = self.context.last_plan_id
                
                if plan_id:
                    value = value.replace("{{plan.id}}", str(plan_id))
                    value = value.replace("{{plan_id}}", str(plan_id))
                    if value == "{{plan.id}}" or value == "{{plan_id}}":
                        return plan_id
                else:
                    raise ValueError(f"Template {value} could not be resolved: plan_id not in context")
            
            if "{{" in value and "}}" in value:
                raise ValueError(f"Unresolved template in value: {value}")
        
        return value

