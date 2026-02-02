"""
Simulation Engine - Motor de simulación para estrategias.

Permite simular la ejecución de una estrategia usando datos de orderbook reales
para estimar PnL, fills y performance antes de ejecutar con dinero real.
"""
import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session

from app.models.strategy import Strategy
from app.models.strategy_event import StrategyEvent
from app.models.event import Event
from app.core.orderbook.models import OrderbookState

logger = logging.getLogger(__name__)


class FillMode(str, Enum):
    """Modos de simulación de fills."""
    CONSERVATIVE = "conservative"  # Solo usa best level
    REALISTIC = "realistic"        # Barre top-N levels según liquidez


@dataclass
class SimulatedFill:
    """Representa un fill simulado."""
    event_id: str
    asset_id: str
    side: str  # "BUY" | "SELL"
    outcome: str  # "YES" | "NO"
    price: Decimal
    size: Decimal
    size_usdc: Decimal
    timestamp: datetime
    fill_mode: FillMode
    levels_swept: int = 1  # Cuántos levels se barrieron


@dataclass
class SimulatedOrder:
    """Representa una orden simulada."""
    event_id: str
    asset_id: str
    side: str
    outcome: str
    target_price: Decimal
    requested_size: Decimal
    requested_size_usdc: Decimal
    fill: Optional[SimulatedFill] = None
    rejected_reason: Optional[str] = None
    is_filled: bool = False
    is_rejected: bool = False


@dataclass
class SimulationResult:
    """Resultado de una simulación."""
    strategy_id: str
    duration_seconds: int
    capital_usdc: Decimal
    fill_mode: FillMode
    
    # Métricas principales
    estimated_pnl: Decimal = Decimal("0")
    orders_created: int = 0
    orders_filled: int = 0
    orders_rejected: int = 0
    total_volume_usdc: Decimal = Decimal("0")
    average_fill_price: Optional[Decimal] = None
    
    # Detalle de fills
    fills_breakdown: List[Dict[str, Any]] = field(default_factory=list)
    
    # Métricas avanzadas
    win_rate: Optional[float] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[float] = None
    
    # Warnings y notas
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para respuesta API."""
        return {
            "strategy_id": self.strategy_id,
            "duration_seconds": self.duration_seconds,
            "capital_usdc": float(self.capital_usdc),
            "fill_mode": self.fill_mode.value,
            "estimated_pnl": float(self.estimated_pnl),
            "orders_created": self.orders_created,
            "orders_filled": self.orders_filled,
            "orders_rejected": self.orders_rejected,
            "total_volume_usdc": float(self.total_volume_usdc),
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price else None,
            "fills_breakdown": self.fills_breakdown,
            "win_rate": self.win_rate,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "sharpe_ratio": self.sharpe_ratio,
            "warnings": self.warnings,
        }


class SimExecutionEngine:
    """
    Motor de simulación de ejecución.
    
    Simula cómo una estrategia se comportaría dados los orderbooks actuales,
    sin ejecutar órdenes reales.
    """
    
    def __init__(self, state_cache_service: 'StateCacheService'):
        self.state_cache = state_cache_service
    
    async def simulate(
        self,
        strategy: Strategy,
        db: Session,
        duration_seconds: int = 3600,
        capital_usdc: float = 10000.0,
        fill_mode: FillMode = FillMode.CONSERVATIVE,
    ) -> SimulationResult:
        """
        Ejecuta una simulación de la estrategia.
        
        Args:
            strategy: Estrategia a simular
            db: Sesión de base de datos
            duration_seconds: Duración de la simulación en segundos
            capital_usdc: Capital disponible para la simulación
            fill_mode: Modo de simulación de fills
            
        Returns:
            SimulationResult con métricas y fills simulados
        """
        result = SimulationResult(
            strategy_id=str(strategy.id),
            duration_seconds=duration_seconds,
            capital_usdc=Decimal(str(capital_usdc)),
            fill_mode=fill_mode,
        )
        
        # Obtener eventos asignados a la estrategia
        strategy_events = db.query(StrategyEvent).filter(
            StrategyEvent.strategy_id == strategy.id
        ).all()
        
        if not strategy_events:
            result.warnings.append("No events assigned to strategy")
            return result
        
        # Para cada evento, simular ejecución
        remaining_capital = Decimal(str(capital_usdc))
        total_fills_value = Decimal("0")
        total_fills_count = 0
        
        for se in strategy_events:
            event = se.event
            if not event:
                continue
            
            # Simular órdenes para este evento
            simulated_orders = await self._simulate_event(
                strategy=strategy,
                event=event,
                available_capital=remaining_capital,
                fill_mode=fill_mode,
                db=db,
            )
            
            for order in simulated_orders:
                result.orders_created += 1
                
                if order.is_filled and order.fill:
                    result.orders_filled += 1
                    result.total_volume_usdc += order.fill.size_usdc
                    total_fills_value += order.fill.price * order.fill.size
                    total_fills_count += 1
                    remaining_capital -= order.fill.size_usdc
                    
                    result.fills_breakdown.append({
                        "event_id": order.event_id,
                        "asset_id": order.asset_id,
                        "side": order.side,
                        "outcome": order.outcome,
                        "price": float(order.fill.price),
                        "size": float(order.fill.size),
                        "size_usdc": float(order.fill.size_usdc),
                        "levels_swept": order.fill.levels_swept,
                        "timestamp": order.fill.timestamp.isoformat(),
                    })
                    
                elif order.is_rejected:
                    result.orders_rejected += 1
        
        # Calcular métricas finales
        if total_fills_count > 0:
            result.average_fill_price = total_fills_value / Decimal(str(total_fills_count))
            
            # Estimar PnL basado en precios de resolución esperados
            # Asumimos que si compramos YES a 0.95 y resuelve a 1.0, ganamos 0.05 por share
            # Esta es una estimación simplificada
            result.estimated_pnl = self._estimate_pnl(result.fills_breakdown)
            
            # Calcular win rate (basado en si el precio de entrada es favorable)
            winning_fills = sum(
                1 for f in result.fills_breakdown 
                if (f["side"] == "BUY" and f["price"] < 0.5) or 
                   (f["side"] == "SELL" and f["price"] > 0.5)
            )
            result.win_rate = winning_fills / total_fills_count if total_fills_count > 0 else None
        
        logger.info(
            f"Simulation completed for strategy {strategy.id}: "
            f"{result.orders_filled}/{result.orders_created} orders filled, "
            f"estimated PnL: {result.estimated_pnl}"
        )
        
        return result
    
    async def _simulate_event(
        self,
        strategy: Strategy,
        event: Event,
        available_capital: Decimal,
        fill_mode: FillMode,
        db: Session,
    ) -> List[SimulatedOrder]:
        """
        Simula la ejecución de órdenes para un evento específico.
        """
        orders = []
        
        # Obtener asset_ids del evento
        asset_ids = self._get_asset_ids(event)
        if not asset_ids:
            return orders
        
        # Para cada asset_id, verificar condiciones y simular orden
        for asset_id in asset_ids:
            # Obtener orderbook del state cache
            orderbook_state = self._get_orderbook_state(asset_id)
            
            if not orderbook_state:
                continue
            
            # Verificar si cumple condiciones de la estrategia
            decision_config = strategy.decision_graph.get("config", {})
            
            # Verificar spread
            max_spread_bps = decision_config.get("max_spread_bps", 200)
            if orderbook_state.spread_bps and orderbook_state.spread_bps > max_spread_bps:
                continue
            
            # Calcular tamaño de orden
            order_usdc = min(
                Decimal(str(decision_config.get("order_usdc", 100))),
                available_capital
            )
            
            if order_usdc <= 0:
                continue
            
            # Determinar lado y precio
            # Para estrategia near-resolution, compramos YES si precio < threshold
            price_threshold = Decimal(str(decision_config.get("price_max", "0.98")))
            
            best_ask = orderbook_state.best_ask_price
            if not best_ask or best_ask >= price_threshold:
                continue
            
            # Simular fill
            simulated_fill = self._simulate_fill(
                asset_id=asset_id,
                side="BUY",
                outcome="YES",
                target_price=best_ask,
                requested_size_usdc=order_usdc,
                orderbook_state=orderbook_state,
                fill_mode=fill_mode,
            )
            
            order = SimulatedOrder(
                event_id=str(event.id),
                asset_id=asset_id,
                side="BUY",
                outcome="YES",
                target_price=best_ask,
                requested_size=order_usdc / best_ask if best_ask > 0 else Decimal("0"),
                requested_size_usdc=order_usdc,
                fill=simulated_fill,
                is_filled=simulated_fill is not None,
            )
            
            orders.append(order)
            
            # Solo una orden por asset_id para simplificar
            break
        
        return orders
    
    def _simulate_fill(
        self,
        asset_id: str,
        side: str,
        outcome: str,
        target_price: Decimal,
        requested_size_usdc: Decimal,
        orderbook_state: OrderbookState,
        fill_mode: FillMode,
    ) -> Optional[SimulatedFill]:
        """
        Simula un fill basado en el estado del orderbook.
        """
        if fill_mode == FillMode.CONSERVATIVE:
            # Solo usa el mejor nivel
            return self._fill_conservative(
                asset_id, side, outcome, target_price, 
                requested_size_usdc, orderbook_state
            )
        else:
            # Barre múltiples niveles
            return self._fill_realistic(
                asset_id, side, outcome, target_price,
                requested_size_usdc, orderbook_state
            )
    
    def _fill_conservative(
        self,
        asset_id: str,
        side: str,
        outcome: str,
        target_price: Decimal,
        requested_size_usdc: Decimal,
        orderbook_state: OrderbookState,
    ) -> Optional[SimulatedFill]:
        """
        Fill conservador: solo usa el mejor nivel disponible.
        """
        if side == "BUY":
            price = orderbook_state.best_ask_price
            # Estimar liquidez disponible en el mejor nivel (conservador: 50% del depth)
            available_usdc = (orderbook_state.ask_depth_usdc_at_50bps or Decimal("0")) * Decimal("0.5")
        else:
            price = orderbook_state.best_bid_price
            available_usdc = (orderbook_state.bid_depth_usdc_at_50bps or Decimal("0")) * Decimal("0.5")
        
        if not price or price <= 0:
            return None
        
        # Limitar por liquidez disponible
        fill_usdc = min(requested_size_usdc, available_usdc)
        if fill_usdc <= 0:
            return None
        
        fill_size = fill_usdc / price
        
        return SimulatedFill(
            event_id="",  # Se llena después
            asset_id=asset_id,
            side=side,
            outcome=outcome,
            price=price,
            size=fill_size,
            size_usdc=fill_usdc,
            timestamp=datetime.now(timezone.utc),
            fill_mode=FillMode.CONSERVATIVE,
            levels_swept=1,
        )
    
    def _fill_realistic(
        self,
        asset_id: str,
        side: str,
        outcome: str,
        target_price: Decimal,
        requested_size_usdc: Decimal,
        orderbook_state: OrderbookState,
    ) -> Optional[SimulatedFill]:
        """
        Fill realista: barre múltiples niveles de liquidez.
        
        Simula el slippage real que ocurriría al ejecutar una orden grande.
        """
        if side == "BUY":
            best_price = orderbook_state.best_ask_price
            # Usar depth total como proxy de liquidez disponible
            total_depth = orderbook_state.ask_depth_usdc_at_50bps or Decimal("0")
        else:
            best_price = orderbook_state.best_bid_price
            total_depth = orderbook_state.bid_depth_usdc_at_50bps or Decimal("0")
        
        if not best_price or best_price <= 0:
            return None
        
        # Simular barrido de niveles
        # Asumimos que cada nivel tiene aproximadamente 20% de la liquidez
        levels_needed = 1
        accumulated_usdc = Decimal("0")
        weighted_price_sum = Decimal("0")
        
        remaining_usdc = requested_size_usdc
        level_depth = total_depth * Decimal("0.2")  # 20% por nivel
        current_price = best_price
        
        while remaining_usdc > 0 and levels_needed <= 5:
            # Liquidez en este nivel
            level_fill = min(remaining_usdc, level_depth)
            accumulated_usdc += level_fill
            weighted_price_sum += current_price * level_fill
            remaining_usdc -= level_fill
            
            # Siguiente nivel tiene peor precio (slippage)
            if side == "BUY":
                current_price = current_price * Decimal("1.005")  # +0.5% slippage por nivel
            else:
                current_price = current_price * Decimal("0.995")  # -0.5% slippage por nivel
            
            levels_needed += 1
        
        if accumulated_usdc <= 0:
            return None
        
        # Precio promedio ponderado
        avg_price = weighted_price_sum / accumulated_usdc
        fill_size = accumulated_usdc / avg_price
        
        return SimulatedFill(
            event_id="",
            asset_id=asset_id,
            side=side,
            outcome=outcome,
            price=avg_price,
            size=fill_size,
            size_usdc=accumulated_usdc,
            timestamp=datetime.now(timezone.utc),
            fill_mode=FillMode.REALISTIC,
            levels_swept=levels_needed - 1,
        )
    
    def _get_asset_ids(self, event: Event) -> List[str]:
        """Obtiene los asset_ids de un evento."""
        asset_ids = []
        
        clob_token_ids = None
        if event.polymarket_payload:
            clob_token_ids = (
                event.polymarket_payload.get("clobTokenIds") or 
                event.polymarket_payload.get("clob_token_ids")
            )
        
        if not clob_token_ids and event.market:
            if event.market.polymarket_payload:
                clob_token_ids = (
                    event.market.polymarket_payload.get("clobTokenIds") or 
                    event.market.polymarket_payload.get("clob_token_ids")
                )
        
        if clob_token_ids:
            if isinstance(clob_token_ids, dict):
                asset_ids.extend(clob_token_ids.values())
            elif isinstance(clob_token_ids, list):
                asset_ids.extend(clob_token_ids)
        
        return asset_ids
    
    def _get_orderbook_state(self, asset_id: str) -> Optional[OrderbookState]:
        """Obtiene el estado del orderbook desde el cache."""
        try:
            # Intentar obtener del state cache
            cache_key = f"orderbook:{asset_id}"
            cached = self.state_cache.get(cache_key)
            
            if cached and isinstance(cached, dict):
                return OrderbookState(
                    asset_id=asset_id,
                    best_bid_price=Decimal(str(cached.get("best_bid_price", 0))) if cached.get("best_bid_price") else None,
                    best_ask_price=Decimal(str(cached.get("best_ask_price", 0))) if cached.get("best_ask_price") else None,
                    spread_bps=cached.get("spread_bps"),
                    bid_depth_usdc_at_50bps=Decimal(str(cached.get("bid_depth_usdc_at_50bps", 0))) if cached.get("bid_depth_usdc_at_50bps") else None,
                    ask_depth_usdc_at_50bps=Decimal(str(cached.get("ask_depth_usdc_at_50bps", 0))) if cached.get("ask_depth_usdc_at_50bps") else None,
                )
            return None
        except Exception as e:
            logger.warning(f"Error getting orderbook state for {asset_id}: {e}")
            return None
    
    def _estimate_pnl(self, fills_breakdown: List[Dict[str, Any]]) -> Decimal:
        """
        Estima el PnL basado en los fills.
        
        Para estrategia near-resolution:
        - Si compramos YES a precio X y resuelve a 1.0, ganamos (1.0 - X) * size
        - Si compramos NO a precio X y resuelve a 0.0, perdemos X * size
        
        Asumimos que el 80% de las veces acertamos (escenario optimista).
        """
        total_pnl = Decimal("0")
        win_probability = Decimal("0.8")  # Asumimos 80% win rate
        
        for fill in fills_breakdown:
            price = Decimal(str(fill["price"]))
            size = Decimal(str(fill["size"]))
            
            if fill["side"] == "BUY" and fill["outcome"] == "YES":
                # Compramos YES: ganamos si resuelve a 1.0
                expected_gain = (Decimal("1.0") - price) * size * win_probability
                expected_loss = price * size * (Decimal("1.0") - win_probability)
                total_pnl += expected_gain - expected_loss
            
            elif fill["side"] == "BUY" and fill["outcome"] == "NO":
                # Compramos NO: ganamos si resuelve a 0.0
                expected_gain = (Decimal("1.0") - price) * size * win_probability
                expected_loss = price * size * (Decimal("1.0") - win_probability)
                total_pnl += expected_gain - expected_loss
        
        return total_pnl
