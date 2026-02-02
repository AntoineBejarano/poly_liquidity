"""
Precheck Node - Valida condiciones antes de ejecutar un ExecutionPlan.

Este nodo valida:
- Frescura del orderbook (staleness)
- Drift del precio (diferencia entre target_price y precio actual)
- Impacto de mercado (impact_bps)
- TTL del plan (no expirado)

Si todas las validaciones pasan, continúa al siguiente nodo (on_pass).
Si alguna falla, va al nodo de fallo (on_fail) y registra la métrica.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.strategy_engine.nodes.base import GraphNode, ConditionalResult, FailureResult
from app.models.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PrecheckResult:
    """Resultado del precheck con detalles."""
    def __init__(self, passed: bool, failures: list = None):
        self.passed = passed
        self.failures = failures or []


class PrecheckNode(GraphNode):
    """
    Nodo que valida precondiciones antes de ejecutar un plan.
    
    Validaciones:
    1. Orderbook staleness: ¿El libro está actualizado?
    2. Price drift: ¿El precio actual está cerca del target_price?
    3. Market impact: ¿El impacto es aceptable para el tamaño?
    4. Plan TTL: ¿El plan no ha expirado?
    """
    
    async def execute(self) -> ConditionalResult:
        """
        Ejecuta las validaciones de precheck.
        
        Config:
            plan_id: str | UUID - ID del plan a validar
            max_book_staleness_ms: int - Máxima antigüedad del orderbook (default: 2000ms)
            drift_bps_limit: int - Máximo drift permitido en bps (default: 100 = 1%)
            max_impact_bps: int - Máximo impacto permitido en bps (default: 200 = 2%)
            skip_orderbook_check: bool - Si True, no valida orderbook (default: False)
        
        Retorna:
            ConditionalResult con condition=True si pasa todas las validaciones
            ConditionalResult con condition=False y data con razones de fallo
        """
        plan_id = self.config.get("plan_id")
        max_staleness_ms = self.config.get("max_book_staleness_ms", 2000)
        drift_bps_limit = self.config.get("drift_bps_limit", 100)
        max_impact_bps = self.config.get("max_impact_bps", 200)
        skip_orderbook_check = self.config.get("skip_orderbook_check", False)
        
        failures = []
        
        # Resolver plan_id si es template
        plan_id = self._resolve_template(plan_id)
        if not plan_id:
            return ConditionalResult(condition=False, data={"failures": ["plan_id is required"]})
        
        # Obtener plan de la DB
        plan = self._get_plan(plan_id)
        if not plan:
            return ConditionalResult(condition=False, data={"failures": [f"Plan {plan_id} not found"]})
        
        # 1. Validar TTL del plan
        ttl_result = self._check_plan_ttl(plan)
        if not ttl_result["passed"]:
            failures.append(ttl_result["reason"])
        
        # 2. Obtener orderbook_state del State Cache
        orderbook_state = None
        if not skip_orderbook_check:
            orderbook_state = await self._get_orderbook_state(plan)
        
        if orderbook_state and not skip_orderbook_check:
            # 3. Validar staleness del orderbook
            staleness_result = self._check_orderbook_staleness(orderbook_state, max_staleness_ms)
            if not staleness_result["passed"]:
                failures.append(staleness_result["reason"])
            
            # 4. Validar price drift para cada leg
            drift_result = self._check_price_drift(plan, orderbook_state, drift_bps_limit)
            if not drift_result["passed"]:
                failures.extend(drift_result["reasons"])
            
            # 5. Validar market impact
            impact_result = self._check_market_impact(plan, orderbook_state, max_impact_bps)
            if not impact_result["passed"]:
                failures.append(impact_result["reason"])
        
        # Registrar resultado
        passed = len(failures) == 0
        
        if not passed:
            logger.warning(
                f"Precheck FAILED for plan {plan_id}: {failures}",
                extra={
                    "component": "precheck",
                    "event": "precheck_failed",
                    "plan_id": str(plan_id),
                    "failures": failures,
                    "trace_id": str(plan.trace_id) if plan and plan.trace_id else None
                }
            )
            # Registrar métrica de fallo
            await self._record_precheck_failure(failures)
            # Emitir evento WebSocket para dashboard en tiempo real
            try:
                from app.api.websocket import broadcast_strategy_event
                if plan and plan.strategy_id:
                    payload = {
                        "plan_id": str(plan.id),
                        "strategy_id": str(plan.strategy_id),
                        "event_id": str(plan.event_id),
                        "failures": failures,
                        "trace_id": str(plan.trace_id) if plan.trace_id else None,
                    }
                    await broadcast_strategy_event(plan.strategy_id, "precheck_failed", payload)
            except Exception as ws_err:
                logger.warning(f"Failed to broadcast precheck_failed: {ws_err}")
        else:
            logger.info(
                f"Precheck PASSED for plan {plan_id}",
                extra={
                    "component": "precheck",
                    "event": "precheck_passed",
                    "plan_id": str(plan_id),
                    "trace_id": str(plan.trace_id) if plan and plan.trace_id else None
                }
            )
        
        return ConditionalResult(
            condition=passed,
            data={"failures": failures, "plan_id": str(plan_id)}
        )
    
    def _resolve_template(self, value: Any) -> Any:
        """Resuelve templates como {{plan.id}} usando valores del contexto."""
        if value is None:
            return None
        
        if isinstance(value, str) and "{{" in value and "}}" in value:
            if "{{plan.id}}" in value or "{{plan_id}}" in value:
                plan_id = getattr(self.context, 'plan_id', None) or getattr(self.context, 'last_plan_id', None)
                if plan_id:
                    return plan_id
                return None
        return value
    
    def _get_plan(self, plan_id) -> Optional[ExecutionPlan]:
        """Obtiene el plan de la base de datos."""
        try:
            if isinstance(plan_id, str):
                plan_id = UUID(plan_id)
            
            db = getattr(self.context, 'db', None)
            if not db:
                logger.warning("No db in context, cannot fetch plan")
                return None
            
            return db.query(ExecutionPlan).filter(ExecutionPlan.id == plan_id).first()
        except Exception as e:
            logger.error(f"Error fetching plan {plan_id}: {e}")
            return None
    
    def _check_plan_ttl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Valida que el plan no haya expirado."""
        if not plan.ttl_ms:
            return {"passed": True}
        
        created_at = plan.created_at
        if not created_at:
            return {"passed": True}
        
        # Si created_at no tiene timezone, asumimos UTC
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        elapsed_ms = (now - created_at).total_seconds() * 1000
        
        if elapsed_ms > plan.ttl_ms:
            return {
                "passed": False,
                "reason": f"plan_ttl_expired: elapsed={elapsed_ms:.0f}ms > ttl={plan.ttl_ms}ms"
            }
        return {"passed": True}
    
    async def _get_orderbook_state(self, plan: ExecutionPlan) -> Optional[Dict[str, Any]]:
        """Obtiene el orderbook_state del State Cache."""
        try:
            state_cache = getattr(self.context, 'state_cache', None)
            if not state_cache:
                return None
            
            # Obtener asset_id del plan o de metadata
            asset_id = None
            if plan.legs:
                # Intentar obtener asset_id del primer leg
                first_leg = plan.legs[0] if plan.legs else {}
                asset_id = first_leg.get("metadata", {}).get("asset_id")
            
            if not asset_id:
                # Intentar desde context.metadata
                metadata = getattr(self.context, 'metadata', {})
                asset_id = metadata.get("asset_id") if isinstance(metadata, dict) else None
            
            if not asset_id:
                return None
            
            cache_key = f"pm.orderbook.{asset_id}"
            return await state_cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Error getting orderbook_state: {e}")
            return None
    
    def _check_orderbook_staleness(self, orderbook_state: Dict[str, Any], max_staleness_ms: int) -> Dict[str, Any]:
        """Valida que el orderbook no esté desactualizado."""
        staleness_ms = orderbook_state.get("staleness_ms")
        if staleness_ms is None:
            # Si no hay staleness, asumimos que está fresco
            return {"passed": True}
        
        if staleness_ms > max_staleness_ms:
            return {
                "passed": False,
                "reason": f"orderbook_stale: staleness={staleness_ms}ms > max={max_staleness_ms}ms"
            }
        return {"passed": True}
    
    def _check_price_drift(self, plan: ExecutionPlan, orderbook_state: Dict[str, Any], drift_bps_limit: int) -> Dict[str, Any]:
        """
        Valida que el precio actual no se haya movido demasiado del target_price.
        
        Para BUY: comparamos con best_ask_price
        Para SELL: comparamos con best_bid_price
        """
        reasons = []
        
        legs = plan.legs or []
        for leg in legs:
            target_price = leg.get("target_price")
            side = leg.get("side", "BUY").upper()
            
            if not target_price:
                continue
            
            # Obtener precio actual según el side
            if side == "BUY":
                current_price = orderbook_state.get("best_ask_price")
            else:
                current_price = orderbook_state.get("best_bid_price")
            
            if current_price is None:
                continue
            
            # Calcular drift en bps
            target = Decimal(str(target_price))
            current = Decimal(str(current_price))
            
            if target == 0:
                continue
            
            drift_bps = abs((current - target) / target) * 10000
            
            if drift_bps > drift_bps_limit:
                reasons.append(
                    f"price_drift: leg={leg.get('leg_id')}, "
                    f"target={target}, current={current}, "
                    f"drift={drift_bps:.0f}bps > limit={drift_bps_limit}bps"
                )
        
        return {
            "passed": len(reasons) == 0,
            "reasons": reasons
        }
    
    def _check_market_impact(self, plan: ExecutionPlan, orderbook_state: Dict[str, Any], max_impact_bps: int) -> Dict[str, Any]:
        """Valida que el impacto de mercado sea aceptable."""
        # Obtener impacto del orderbook para el tamaño del plan
        # Usamos impact_bps_for_usdc_1000 como proxy
        impact_bps = orderbook_state.get("impact_bps_for_usdc_1000")
        
        if impact_bps is None:
            # Si no hay dato de impacto, dejamos pasar
            return {"passed": True}
        
        if impact_bps > max_impact_bps:
            return {
                "passed": False,
                "reason": f"market_impact_high: impact={impact_bps}bps > max={max_impact_bps}bps"
            }
        return {"passed": True}
    
    async def _record_precheck_failure(self, failures: list):
        """Registra métrica de precheck fallido."""
        try:
            # Intentar usar metrics_service del contexto o global
            metrics_service = getattr(self.context, 'metrics_service', None)
            if not metrics_service:
                # Intentar importar el global
                try:
                    from app.core.metrics import metrics_service as global_metrics
                    metrics_service = global_metrics
                except ImportError:
                    pass
            
            if metrics_service and hasattr(metrics_service, 'collector'):
                for failure in failures:
                    # Extraer la razón principal (antes del :)
                    reason = failure.split(":")[0] if ":" in failure else failure
                    await metrics_service.collector.store.store_metric(
                        metric_name="plans_failed_precheck_total",
                        value=1,
                        labels={"reason": reason},
                        component="precheck"
                    )
        except Exception as e:
            logger.warning(f"Error recording precheck failure metric: {e}")
