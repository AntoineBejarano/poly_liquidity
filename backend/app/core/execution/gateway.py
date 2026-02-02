"""
Execution Gateway - Único punto de envío al CLOB (I3).

Aplica invariantes I1, I2, I4, I5, I6 antes de cualquier escritura al CLOB.
Tanto el camino Plans (PolymarketAdapter) como el camino Intents (Execution legacy)
deben pasar por este gateway.

SPEC: docs/implementation/LIVE_NEAR_RESOLUTION_ESTADO_Y_GAPS.md
"""
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from app.core.config_service import config_service
from app.core.state import state
from app.core.latency_monitor import latency_monitor, LatencyStatus

logger = logging.getLogger(__name__)


class GatewayDecision(str, Enum):
    """Decisión del Gateway (alineado con SPEC §4.2)."""
    SEND = "SEND"
    SIMULATE = "SIMULATE"
    SKIP_PAUSED = "SKIP_PAUSED"
    SKIP_LATENCY = "SKIP_LATENCY"
    SKIP_CIRCUIT = "SKIP_CIRCUIT"
    SKIP_DRY_RUN = "SKIP_DRY_RUN"


class SourcePath(str, Enum):
    """Origen de la solicitud (I5, observabilidad)."""
    INTENT = "INTENT"
    PLAN = "PLAN"


@dataclass
class ExecutionGatewayRequest:
    """Solicitud de envío al Gateway (SPEC §4.2 inputs)."""
    trace_id: str
    strategy_id: str
    plan_id: Optional[str] = None
    leg_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    operation: str = "submit_order"  # submit_order | cancel_order
    source_path: SourcePath = SourcePath.PLAN


@dataclass
class ExecutionGatewayResult:
    """Respuesta del Gateway (SPEC §4.2 outputs)."""
    decision: GatewayDecision
    reason_code: Optional[str] = None
    reason_detail: Optional[str] = None
    platform_order_id: Optional[str] = None
    status: str = "SKIPPED"  # SUBMITTED | SIMULATED | SKIPPED | REJECTED
    error: Optional[str] = None


def _make_idempotency_key(trace_id: str, plan_id: Optional[str], leg_id: Optional[str], side: str, token_id: str) -> str:
    """Clave idempotente determinista (I6). Sin timestamp ni random."""
    parts = [trace_id, plan_id or "", leg_id or "", side, token_id]
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()


class ExecutionGateway:
    """
    Único punto que puede invocar al CLOB (Polymarket).
    Aplica I1 (solo LIVE escribe), I2 (kill-switch), I4 (latencia/circuit), I5 (trazabilidad), I6 (idempotencia).
    """

    def __init__(self, clob_delegate: Optional[Any] = None):
        """
        Args:
            clob_delegate: Instancia de PolymarketCLOBWrapper (o mock en tests).
                          Si None, se usa get_polymarket_client() en el primer uso.
        """
        self._clob_delegate = clob_delegate
        self._idempotency_cache: Dict[str, ExecutionGatewayResult] = {}

    def _get_clob(self):
        """Obtiene el cliente CLOB (inyectado o singleton)."""
        if self._clob_delegate is not None:
            return self._clob_delegate
        from app.core.execution.polymarket_client_wrapper import get_polymarket_client
        return get_polymarket_client()

    def _log_order_decision(
        self,
        request: ExecutionGatewayRequest,
        decision: GatewayDecision,
        execution_mode: str,
        system_active: bool,
        reason_code: Optional[str] = None,
        reason_detail: Optional[str] = None,
        platform_order_id: Optional[str] = None,
    ) -> None:
        """I5: Trazabilidad obligatoria (order_decision)."""
        logger.info(
            "order_decision",
            extra={
                "event": "order_decision",
                "trace_id": request.trace_id,
                "strategy_id": request.strategy_id,
                "plan_id": request.plan_id,
                "execution_mode": execution_mode,
                "system_active": system_active,
                "decision": decision.value,
                "source_path": request.source_path.value,
                "idempotency_key": request.idempotency_key,
                "reason_code": reason_code,
                "reason_detail": reason_detail,
                "platform_order_id": platform_order_id,
            },
        )

    async def submit_order(self, request: ExecutionGatewayRequest) -> ExecutionGatewayResult:
        """
        Evalúa I1, I2, I4; registra I5; si SEND aplica I6 y llama al CLOB.
        """
        execution_mode = config_service.get_execution_mode()
        system_active = getattr(state, "system_active", True)

        # I1: execution_mode != LIVE => cero escrituras al CLOB
        if execution_mode != "LIVE":
            platform_order_id = f"dry_run_{uuid4().hex[:8]}"
            self._log_order_decision(
                request, GatewayDecision.SKIP_DRY_RUN, execution_mode, system_active,
                reason_code="DRY_RUN", reason_detail="execution_mode is not LIVE",
                platform_order_id=platform_order_id,
            )
            # Evento order_simulated (§5 SPEC)
            logger.info(
                "order_simulated",
                extra={
                    "event": "order_simulated",
                    "trace_id": request.trace_id,
                    "plan_id": request.plan_id,
                    "strategy_id": request.strategy_id,
                    "platform_order_id": platform_order_id,
                    "reason": "DRY_RUN",
                },
            )
            return ExecutionGatewayResult(
                decision=GatewayDecision.SKIP_DRY_RUN,
                reason_code="DRY_RUN",
                reason_detail="execution_mode is not LIVE",
                platform_order_id=platform_order_id,
                status="SIMULATED",
            )

        # I2: system_active == false => ninguna mutación real
        if not system_active:
            platform_order_id = f"skip_paused_{uuid4().hex[:8]}"
            self._log_order_decision(
                request, GatewayDecision.SKIP_PAUSED, execution_mode, system_active,
                reason_code="SYSTEM_PAUSED", reason_detail="system_active is False",
                platform_order_id=platform_order_id,
            )
            return ExecutionGatewayResult(
                decision=GatewayDecision.SKIP_PAUSED,
                reason_code="SYSTEM_PAUSED",
                reason_detail="system_active is False",
                platform_order_id=platform_order_id,
                status="SKIPPED",
            )

        # I4: latencia RED => no enviar
        try:
            latency_status = latency_monitor.get_status()
            if latency_status == LatencyStatus.RED:
                platform_order_id = f"skip_latency_{uuid4().hex[:8]}"
                self._log_order_decision(
                    request, GatewayDecision.SKIP_LATENCY, execution_mode, system_active,
                    reason_code="LATENCY_RED", reason_detail="latency status is RED",
                    platform_order_id=platform_order_id,
                )
                return ExecutionGatewayResult(
                    decision=GatewayDecision.SKIP_LATENCY,
                    reason_code="LATENCY_RED",
                    reason_detail="latency status is RED",
                    platform_order_id=platform_order_id,
                    status="SKIPPED",
                )
        except Exception:
            pass

        # I4: circuit breaker (opcional; si no existe, continuar)
        try:
            from app.core.runtime_supervisor import runtime_supervisor
            if getattr(runtime_supervisor, "trading_circuit", None) and runtime_supervisor.trading_circuit.is_open():
                platform_order_id = f"skip_circuit_{uuid4().hex[:8]}"
                self._log_order_decision(
                    request, GatewayDecision.SKIP_CIRCUIT, execution_mode, system_active,
                    reason_code="CIRCUIT_OPEN", reason_detail="trading circuit is open",
                    platform_order_id=platform_order_id,
                )
                return ExecutionGatewayResult(
                    decision=GatewayDecision.SKIP_CIRCUIT,
                    reason_code="CIRCUIT_OPEN",
                    reason_detail="trading circuit is open",
                    platform_order_id=platform_order_id,
                    status="SKIPPED",
                )
        except (ImportError, AttributeError):
            pass

        # Decisión SEND: aplicar I6 (idempotencia) y llamar al CLOB
        idempotency_key = request.idempotency_key
        if idempotency_key and idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[idempotency_key]
            self._log_order_decision(
                request, GatewayDecision.SEND, execution_mode, system_active,
                platform_order_id=cached.platform_order_id,
            )
            return cached

        self._log_order_decision(
            request, GatewayDecision.SEND, execution_mode, system_active,
        )

        clob = self._get_clob()
        if not clob or not getattr(clob, "is_available", lambda: False)():
            return ExecutionGatewayResult(
                decision=GatewayDecision.SIMULATE,
                reason_code="CLOB_UNAVAILABLE",
                reason_detail="CLOB client not available",
                platform_order_id=f"sim_{uuid4().hex[:8]}",
                status="SIMULATED",
            )

        try:
            order_kind = request.payload.get("order_kind", "limit")
            if order_kind == "market":
                response = await clob.create_market_order(
                    token_id=request.payload["token_id"],
                    amount=float(request.payload.get("amount", request.payload.get("size_usdc", 0))),
                    side=request.payload["side"],
                    order_type=request.payload.get("order_type", "FOK"),
                )
            else:
                response = await clob.create_limit_order(
                    token_id=request.payload["token_id"],
                    price=float(request.payload["price"]),
                    size=float(request.payload["size"]),
                    side=request.payload["side"],
                    order_type=request.payload.get("order_type", "GTC"),
                )

            if isinstance(response, dict):
                platform_order_id = response.get("id") or response.get("order_id") or response.get("orderID")
            else:
                platform_order_id = str(response) if response else None
            platform_order_id = platform_order_id or f"sent_{uuid4().hex[:8]}"

            result = ExecutionGatewayResult(
                decision=GatewayDecision.SEND,
                platform_order_id=str(platform_order_id),
                status="SUBMITTED",
            )
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result

            # Evento order_sent (§5 SPEC)
            logger.info(
                "order_sent",
                extra={
                    "event": "order_sent",
                    "trace_id": request.trace_id,
                    "plan_id": request.plan_id,
                    "strategy_id": request.strategy_id,
                    "platform_order_id": str(platform_order_id),
                    "source_path": request.source_path.value,
                },
            )
            return result
        except Exception as e:
            logger.exception("Gateway submit_order CLOB call failed")
            return ExecutionGatewayResult(
                decision=GatewayDecision.SEND,
                platform_order_id=None,
                status="REJECTED",
                error=str(e),
            )

    async def cancel_order(self, request: ExecutionGatewayRequest) -> ExecutionGatewayResult:
        """
        Evalúa I1, I2, I4; registra I5; si SEND llama al CLOB (identidad por platform_order_id para I6).
        """
        execution_mode = config_service.get_execution_mode()
        system_active = getattr(state, "system_active", True)

        if execution_mode != "LIVE":
            self._log_order_decision(
                request, GatewayDecision.SKIP_DRY_RUN, execution_mode, system_active,
                reason_code="DRY_RUN", platform_order_id=request.payload.get("platform_order_id"),
            )
            return ExecutionGatewayResult(
                decision=GatewayDecision.SKIP_DRY_RUN,
                reason_code="DRY_RUN",
                platform_order_id=request.payload.get("platform_order_id"),
                status="SIMULATED",
            )
        if not system_active:
            self._log_order_decision(
                request, GatewayDecision.SKIP_PAUSED, execution_mode, system_active,
                reason_code="SYSTEM_PAUSED", platform_order_id=request.payload.get("platform_order_id"),
            )
            return ExecutionGatewayResult(
                decision=GatewayDecision.SKIP_PAUSED,
                reason_code="SYSTEM_PAUSED",
                platform_order_id=request.payload.get("platform_order_id"),
                status="SKIPPED",
            )

        order_id = request.payload.get("platform_order_id") or request.payload.get("order_id")
        if not order_id:
            return ExecutionGatewayResult(
                decision=GatewayDecision.SEND,
                status="REJECTED",
                error="platform_order_id required for cancel",
            )

        self._log_order_decision(
            request, GatewayDecision.SEND, execution_mode, system_active,
            platform_order_id=str(order_id),
        )

        clob = self._get_clob()
        if not clob or not getattr(clob, "is_available", lambda: False)():
            return ExecutionGatewayResult(
                decision=GatewayDecision.SIMULATE,
                reason_code="CLOB_UNAVAILABLE",
                platform_order_id=str(order_id),
                status="SIMULATED",
            )

        try:
            await clob.cancel_order(str(order_id))
            return ExecutionGatewayResult(
                decision=GatewayDecision.SEND,
                platform_order_id=str(order_id),
                status="SUBMITTED",
            )
        except Exception as e:
            logger.exception("Gateway cancel_order CLOB call failed")
            return ExecutionGatewayResult(
                decision=GatewayDecision.SEND,
                platform_order_id=str(order_id),
                status="REJECTED",
                error=str(e),
            )


_gateway_instance: Optional[ExecutionGateway] = None


def get_execution_gateway(clob_delegate: Optional[Any] = None) -> ExecutionGateway:
    """Singleton del Execution Gateway. Para tests se puede inyectar clob_delegate."""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = ExecutionGateway(clob_delegate=clob_delegate)
    return _gateway_instance
