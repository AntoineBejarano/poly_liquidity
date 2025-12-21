"""
Proveedor de señales para estrategias de Liquidity Provider.

Implementa 10 indicadores técnicos + 4 indicadores de rentabilidad (Quant Engine)
con validación de freshness y memoización.
"""
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
import logging
import statistics

from app.core.strategy_engine.indicators.base import SignalProvider

logger = logging.getLogger(__name__)


class LiquidityProvider(SignalProvider):
    """
    Proveedor de señales para estrategias de Liquidity Provider.
    
    Implementa 10 indicadores técnicos + 4 indicadores de rentabilidad (Quant Engine):
    
    Indicadores Técnicos:
    - book_imbalance: Desequilibrio entre ofertas y demandas
    - toxic_flow: Proporción de trades en contra de nuestra posición
    - inventory_skew: Desbalance de posición actual vs objetivo
    - price_drift: Cambio de precio en ventana temporal
    - spread_elasticity: Cambio de spread vs volumen
    - cancel_rate: Proporción de órdenes canceladas
    - rel_liquidity: Liquidez relativa vs promedio histórico
    - tw_volatility: Volatilidad ponderada por tiempo
    - res_gap: Diferencia entre precio de mercado y precio esperado post-resolución
    - slippage_impact: Impacto estimado de slippage
    
    Indicadores de Rentabilidad (Quant Engine):
    - expected_roi_at_depth: ROI medio ponderado al comprar X cantidad de contratos
    - capital_absorption_capacity: Capital máximo desplegable manteniendo ROI >= threshold
    - time_value_score: Ratio de eficiencia (ROI / tiempo hasta resolución)
    - slippage_impact_100k: Impacto de slippage para órdenes de gran tamaño
    """
    
    def validate_data(self) -> bool:
        """
        Valida que exista market_state mínimo.
        
        Returns:
            True si los datos necesarios están disponibles
        """
        return self.market_state is not None
    
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula todos los indicadores (técnicos + rentabilidad).
        
        ⚠️ ALERTA DE COMBATE: Usa memoización para evitar cálculos redundantes.
        
        Returns:
            Dict con todos los indicadores calculados (None si no se puede calcular)
        """
        if not self.validate_data():
            return self._empty_signals()
        
        # Limpiar cache al inicio de cada cálculo (nuevo tick)
        self.clear_memo_cache()
        
        # Indicadores técnicos (existentes)
        technical_signals = {
            "book_imbalance": self._calculate_book_imbalance(),
            "toxic_flow": self._calculate_toxic_flow(),
            "inventory_skew": self._calculate_inventory_skew(),
            "price_drift": self._calculate_price_drift(),
            "spread_elasticity": self._calculate_spread_elasticity(),
            "cancel_rate": self._calculate_cancel_rate(),
            "rel_liquidity": self._calculate_rel_liquidity(),
            "tw_volatility": self._calculate_tw_volatility(),
            "res_gap": self._calculate_res_gap(),
            "slippage_impact": self._calculate_slippage_impact(),
        }
        
        # Indicadores de rentabilidad (nuevos - Quant Engine)
        roi_threshold = self.risk_state.get("min_roi_threshold", 0.06) if self.risk_state else 0.06
        capacity = self._calculate_capital_absorption_capacity(roi_threshold)
        
        profitability_signals = {
            "expected_roi_at_depth": self._calculate_expected_roi_at_depth(capacity) if capacity else None,
            "capital_absorption_capacity": capacity,
            "time_value_score": self._calculate_time_value_score(),
            "slippage_impact_100k": self._calculate_slippage_impact_100k(),
        }
        
        return {**technical_signals, **profitability_signals}
    
    def _empty_signals(self) -> Dict[str, Optional[float]]:
        """
        Retorna dict con todas las señales en None.
        
        Returns:
            Dict con todas las claves de indicadores en None
        """
        return {key: None for key in [
            "book_imbalance", "toxic_flow", "inventory_skew",
            "price_drift", "spread_elasticity", "cancel_rate",
            "rel_liquidity", "tw_volatility", "res_gap", "slippage_impact",
            # Indicadores de rentabilidad (Quant Engine)
            "expected_roi_at_depth", "capital_absorption_capacity",
            "time_value_score", "slippage_impact_100k"
        ]}
    
    def _calculate_book_imbalance(self) -> Optional[float]:
        """
        Calcula book_imbalance: (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        
        Rango: [-1, 1] donde 0 = balance perfecto
        """
        if not self.market_state:
            return None
        
        # ⚠️ Validar freshness del market_state
        if not self.check_data_freshness(self.market_state, max_age_ms=5000):
            logger.warning("market_state is stale, skipping book_imbalance calculation")
            return None
        
        # Obtener orderbook desde orderbook_snapshot o directamente
        orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
        if not orderbook:
            return None
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return None
        
        # Calcular volúmenes totales
        total_bid_volume = sum(float(bid.get("size", 0)) for bid in bids)
        total_ask_volume = sum(float(ask.get("size", 0)) for ask in asks)
        
        if total_bid_volume + total_ask_volume == 0:
            return None
        
        imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        return imbalance
    
    def _calculate_toxic_flow(self) -> Optional[float]:
        """
        Calcula toxic_flow: trades_against_us / total_trades en ventana temporal.
        
        Rango: [0, 1] donde 0 = flujo favorable, 1 = flujo tóxico
        """
        if not self.market_state:
            return None
        
        # Obtener trades recientes
        recent_trades = self.market_state.get("recent_trades", [])
        if not recent_trades:
            return None
        
        # Obtener nuestra posición actual para determinar qué es "contra nosotros"
        risk_state = self.risk_state
        if not risk_state:
            return None
        
        current_position = risk_state.get("current_position", 0)
        if current_position == 0:
            # Sin posición, no hay flujo tóxico
            return 0.0
        
        # Determinar dirección de posición (positiva = long, negativa = short)
        # Asumimos que posición positiva significa que estamos comprados (YES)
        # Trades de venta (SELL) son contra nosotros si estamos long
        trades_against = 0
        total_trades = len(recent_trades)
        
        if total_trades == 0:
            return None
        
        for trade in recent_trades:
            side = trade.get("side", "").upper()
            # Si estamos long (posición positiva) y hay ventas, es tóxico
            # Si estamos short (posición negativa) y hay compras, es tóxico
            if (current_position > 0 and side == "SELL") or (current_position < 0 and side == "BUY"):
                trades_against += 1
        
        toxic_flow = trades_against / total_trades
        return toxic_flow
    
    def _calculate_inventory_skew(self) -> Optional[float]:
        """
        ⚠️ ALERTA DE COMBATE: Calcula inventory_skew con sincronización de órdenes pendientes.
        
        Fórmula: abs(effective_position - target_position) / max_position
        Rango: [0, 1] donde 0 = posición óptima, 1 = desbalance máximo
        """
        if not self.risk_state:
            return None
        
        # ⚠️ CRÍTICO: Validar freshness del risk_state (max 2 segundos)
        if not self.check_data_freshness(self.risk_state, max_age_ms=2000):
            logger.warning("risk_state is stale, cannot calculate inventory_skew safely")
            return None
        
        current_position = self.risk_state.get("current_position", 0)
        target_position = self.risk_state.get("target_position", 0)
        max_position = self.risk_state.get("max_position", 1)
        
        if max_position == 0:
            return None
        
        # ⚠️ Ajustar con órdenes pendientes
        pending_orders = self.risk_state.get("pending_orders", [])
        pending_position_delta = sum(
            float(order.get("size", 0)) * (1 if order.get("side", "").upper() == "BUY" else -1)
            for order in pending_orders
            if order.get("status") in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]
        )
        
        effective_position = current_position + pending_position_delta
        
        # Calcular skew
        position_diff = abs(effective_position - target_position)
        skew = position_diff / max_position if max_position > 0 else 1.0
        
        return min(skew, 1.0)  # Clamp a [0, 1]
    
    def _calculate_price_drift(self) -> Optional[float]:
        """
        Calcula price_drift: (current_price - price_N_minutes_ago) / price_N_minutes_ago
        
        Rango: [-∞, ∞] (normalmente [-0.1, 0.1] para cambios del 10%)
        """
        if not self.market_state:
            return None
        
        current_price = self.market_state.get("last_price")
        if current_price is None:
            return None
        
        # Obtener historial de precios procesado (memoizado)
        price_history = self._get_price_history_processed()
        if not price_history or len(price_history) < 2:
            return None
        
        # Buscar precio de hace N minutos (ej. 5 minutos)
        now = datetime.utcnow()
        target_time = now - timedelta(minutes=5)
        
        # Buscar el precio más cercano a target_time
        price_n_minutes_ago = None
        for entry in reversed(price_history):  # Empezar desde el más reciente
            entry_time = entry.get("timestamp")
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    continue
            elif isinstance(entry_time, (int, float)):
                if entry_time > 1e10:
                    entry_time = datetime.fromtimestamp(entry_time / 1000)
                else:
                    entry_time = datetime.fromtimestamp(entry_time)
            
            if entry_time <= target_time:
                price_n_minutes_ago = entry.get("price")
                break
        
        if price_n_minutes_ago is None:
            # Usar el precio más antiguo disponible
            price_n_minutes_ago = price_history[0].get("price")
        
        if price_n_minutes_ago is None or price_n_minutes_ago == 0:
            return None
        
        drift = (current_price - price_n_minutes_ago) / price_n_minutes_ago
        return drift
    
    def _calculate_spread_elasticity(self) -> Optional[float]:
        """
        Calcula spread_elasticity: delta_spread / delta_volume
        
        Rango: [0, ∞] donde valores altos = spread inelástico (malo)
        """
        if not self.market_state:
            return None
        
        # Obtener spread y volumen actual
        current_spread = self.market_state.get("spread")
        current_volume = self.market_state.get("volume") or self.market_state.get("volume_24h", 0)
        
        if current_spread is None:
            return None
        
        # Obtener valores históricos (simplificado: usar valores anteriores si están disponibles)
        historical_data = self.market_state.get("historical_data", {})
        if not historical_data:
            return None
        
        previous_spread = historical_data.get("previous_spread")
        previous_volume = historical_data.get("previous_volume", 0)
        
        if previous_spread is None:
            return None
        
        delta_spread = current_spread - previous_spread
        delta_volume = current_volume - previous_volume
        
        if delta_volume == 0:
            return None
        
        elasticity = abs(delta_spread / delta_volume) if delta_volume != 0 else None
        return elasticity
    
    def _calculate_cancel_rate(self) -> Optional[float]:
        """
        Calcula cancel_rate: cancelled_orders / (executed_orders + cancelled_orders)
        
        Rango: [0, 1] donde 0 = todas ejecutadas, 1 = todas canceladas
        """
        if not self.risk_state:
            return None
        
        order_history = self.risk_state.get("order_history", [])
        if not order_history:
            return None
        
        cancelled = sum(1 for order in order_history if order.get("status") in ["CANCELLED", "REJECTED"])
        executed = sum(1 for order in order_history if order.get("status") in ["FILLED", "PARTIALLY_FILLED"])
        
        total = cancelled + executed
        if total == 0:
            return None
        
        cancel_rate = cancelled / total
        return cancel_rate
    
    def _calculate_rel_liquidity(self) -> Optional[float]:
        """
        Calcula rel_liquidity: current_liquidity / average_liquidity_24h
        
        Rango: [0, ∞] donde 1 = liquidez normal
        """
        if not self.market_state:
            return None
        
        # Calcular liquidez actual (suma de volúmenes en orderbook)
        orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
        if not orderbook:
            return None
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        current_liquidity = sum(float(bid.get("size", 0)) for bid in bids) + sum(float(ask.get("size", 0)) for ask in asks)
        
        # Obtener promedio histórico
        avg_liquidity_24h = self.market_state.get("average_liquidity_24h")
        if avg_liquidity_24h is None:
            # Intentar calcular desde historial
            liquidity_history = self.market_state.get("liquidity_history", [])
            if liquidity_history:
                avg_liquidity_24h = statistics.mean(liquidity_history)
            else:
                return None
        
        if avg_liquidity_24h == 0:
            return None
        
        rel_liquidity = current_liquidity / avg_liquidity_24h
        return rel_liquidity
    
    def _calculate_tw_volatility(self) -> Optional[float]:
        """
        Calcula tw_volatility: Volatilidad ponderada por tiempo en ventana reciente.
        
        Rango: [0, ∞]
        """
        price_history = self._get_price_history_processed()
        if not price_history or len(price_history) < 2:
            return None
        
        # Calcular desviación estándar de precios ponderada por tiempo
        prices = [entry.get("price") for entry in price_history if entry.get("price") is not None]
        if len(prices) < 2:
            return None
        
        # Calcular volatilidad (desviación estándar de cambios porcentuales)
        price_changes = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                change = abs((prices[i] - prices[i-1]) / prices[i-1])
                price_changes.append(change)
        
        if not price_changes:
            return None
        
        volatility = statistics.stdev(price_changes) if len(price_changes) > 1 else price_changes[0]
        return volatility
    
    def _calculate_res_gap(self) -> Optional[float]:
        """
        Calcula res_gap: abs(market_price - expected_resolution_price)
        
        Rango: [0, 1]
        """
        if not self.market_state:
            return None
        
        market_price = self.market_state.get("last_price")
        if market_price is None:
            return None
        
        # Obtener precio esperado post-resolución
        expected_price = None
        
        # Intentar desde event_state
        if self.event_state:
            confirmed_prob = self.event_state.get("confirmed_outcome_probability")
            if confirmed_prob is not None:
                expected_price = confirmed_prob
        
        # Intentar desde external_data
        if expected_price is None and self.external_data:
            expected_price = self.external_data.get("expected_resolution_price")
        
        if expected_price is None:
            return None
        
        gap = abs(market_price - expected_price)
        return min(gap, 1.0)  # Clamp a [0, 1]
    
    def _calculate_slippage_impact(self) -> Optional[float]:
        """
        Calcula slippage_impact: (execution_price - mid_price) / mid_price para orden de referencia
        
        Rango: [-∞, ∞] (normalmente [-0.05, 0.05] para 5% de slippage)
        """
        if not self.market_state:
            return None
        
        # Obtener mid price
        best_bid = self.market_state.get("best_bid")
        best_ask = self.market_state.get("best_ask")
        
        if best_bid is None or best_ask is None:
            # Intentar calcular desde orderbook
            orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
            if orderbook:
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                if bids and asks:
                    best_bid = float(bids[0].get("price", 0))
                    best_ask = float(asks[0].get("price", 0))
        
        if best_bid is None or best_ask is None:
            return None
        
        mid_price = (best_bid + best_ask) / 2
        if mid_price == 0:
            return None
        
        # Calcular precio de ejecución teórico para orden de referencia (ej. 1000 shares)
        reference_size = 1000
        orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
        
        if not orderbook:
            return None
        
        # Simular ejecución de orden de referencia
        # Simplificado: usar mejor precio disponible
        execution_price = best_ask  # Asumimos compra (peor caso)
        
        slippage = (execution_price - mid_price) / mid_price
        return slippage
    
    # ========== Indicadores de Rentabilidad (Quant Engine) ==========
    
    def _calculate_expected_roi_at_depth(self, capital_amount: float) -> Optional[float]:
        """
        Calcula ROI medio ponderado al comprar capital_amount de contratos.
        
        Fórmula: ROI_medio = Σ(roi_nivel_i * capital_nivel_i) / Σ(capital_nivel_i)
        donde roi_nivel_i = (1.0 - precio_nivel_i) / precio_nivel_i
        
        Args:
            capital_amount: Cantidad de capital a desplegar (en USDC)
        
        Returns:
            ROI medio ponderado (ej. 0.0612 = 6.12%)
        """
        if not self.market_state:
            return None
        
        orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
        if not orderbook:
            return None
        
        bids = orderbook.get("bids", [])
        if not bids:
            return None
        
        # Obtener precio de resolución esperado
        # Intentar desde event_state primero, luego external_data, finalmente asumir 1.0
        resolution_price = 1.0  # Default: asumimos que el evento se resuelve a 1.0 (YES gana)
        
        if self.event_state:
            confirmed_prob = self.event_state.get("confirmed_outcome_probability")
            if confirmed_prob is not None:
                resolution_price = float(confirmed_prob)
        
        if resolution_price == 1.0 and self.external_data:
            expected_price = self.external_data.get("expected_resolution_price")
            if expected_price is not None:
                resolution_price = float(expected_price)
        
        total_roi_weighted = 0.0
        total_capital_used = 0.0
        remaining_capital = capital_amount
        
        # Recorrer el libro desde el mejor precio hacia abajo
        for bid in bids:
            if remaining_capital <= 0:
                break
            
            price = float(bid.get("price", 0))
            size = float(bid.get("size", 0))
            
            if price <= 0 or size <= 0:
                continue
            
            available_capital = price * size  # Capital necesario para comprar este nivel
            
            # Calcular cuánto capital usar de este nivel
            capital_to_use = min(remaining_capital, available_capital)
            contracts_to_buy = capital_to_use / price
            
            # Calcular ROI de este nivel
            if price > 0:
                roi_level = (resolution_price - price) / price
            else:
                continue
            
            # Acumular ROI ponderado
            total_roi_weighted += roi_level * capital_to_use
            total_capital_used += capital_to_use
            remaining_capital -= capital_to_use
        
        if total_capital_used == 0:
            return None
        
        expected_roi = total_roi_weighted / total_capital_used
        return expected_roi
    
    def _calculate_capital_absorption_capacity(self, roi_threshold: float = 0.06) -> Optional[float]:
        """
        Calcula capacidad máxima de absorción manteniendo ROI >= threshold.
        
        Usa búsqueda binaria para encontrar el máximo capital donde
        expected_roi_at_depth(capital) >= roi_threshold.
        
        Args:
            roi_threshold: ROI mínimo aceptable (default: 0.06 = 6%)
        
        Returns:
            Capital máximo desplegable (en USDC)
        """
        max_capital = self.risk_state.get("max_capital_per_event", 100000) if self.risk_state else 100000
        
        # Búsqueda binaria para encontrar el máximo capital
        low = 0.0
        high = max_capital
        best_capacity = 0.0
        tolerance = 100.0  # Tolerancia de $100
        max_iterations = 50  # Límite de seguridad
        
        iteration = 0
        while high - low > tolerance and iteration < max_iterations:
            iteration += 1
            mid = (low + high) / 2
            roi = self._calculate_expected_roi_at_depth(mid)
            
            if roi is None:
                # Si no se puede calcular ROI, reducir el rango
                high = mid
                continue
            
            if roi >= roi_threshold:
                best_capacity = mid
                low = mid
            else:
                high = mid
        
        return best_capacity if best_capacity > 0 else None
    
    def _calculate_time_value_score(self) -> Optional[float]:
        """
        Calcula score de eficiencia tiempo-valor.
        
        Fórmula: expected_roi / time_to_resolution_minutes
        Prioriza ganancias rápidas.
        
        Returns:
            Score de eficiencia (ROI por minuto)
        """
        if not self.event_state:
            return None
        
        # Calcular tiempo hasta resolución
        close_time = self.event_state.get("close_time") or self.event_state.get("resolution_time")
        if not close_time:
            return None
        
        # Parsear timestamp
        if isinstance(close_time, str):
            try:
                # fromisoformat puede retornar datetime con o sin timezone
                close_time = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
        elif isinstance(close_time, (int, float)):
            if close_time > 1e10:  # Milisegundos
                close_time = datetime.fromtimestamp(close_time / 1000, tz=timezone.utc)
            else:  # Segundos
                close_time = datetime.fromtimestamp(close_time, tz=timezone.utc)
        elif not isinstance(close_time, datetime):
            return None
        
        # Asegurar que ambos datetimes tengan timezone para poder restarlos
        if close_time.tzinfo is None:
            # Si close_time no tiene timezone, asumir UTC
            close_time = close_time.replace(tzinfo=timezone.utc)
        
        # Usar datetime.now(timezone.utc) para obtener datetime con timezone
        now = datetime.now(timezone.utc)
        time_remaining = (close_time - now).total_seconds() / 60  # En minutos
        if time_remaining <= 0:
            return None
        
        # Obtener ROI esperado usando capacidad de absorción
        roi_threshold = self.risk_state.get("min_roi_threshold", 0.06) if self.risk_state else 0.06
        capacity = self._calculate_capital_absorption_capacity(roi_threshold)
        if capacity is None or capacity == 0:
            return None
        
        expected_roi = self._calculate_expected_roi_at_depth(capacity)
        if expected_roi is None:
            return None
        
        time_value_score = expected_roi / time_remaining
        return time_value_score
    
    def _calculate_slippage_impact_100k(self) -> Optional[float]:
        """
        Calcula impacto de slippage para orden de gran tamaño (basada en balance disponible).
        
        Similar a slippage_impact pero calculado para el tamaño completo de
        capital_absorption_capacity.
        
        Returns:
            Impacto de slippage como ratio (ej. 0.004 = 0.4%)
        """
        if not self.market_state:
            return None
        
        # Obtener capacidad de absorción (tamaño de orden)
        roi_threshold = self.risk_state.get("min_roi_threshold", 0.06) if self.risk_state else 0.06
        capacity = self._calculate_capital_absorption_capacity(roi_threshold)
        if capacity is None or capacity == 0:
            return None
        
        # Obtener precio medio actual
        best_bid = self.market_state.get("best_bid")
        best_ask = self.market_state.get("best_ask")
        
        if best_bid is None or best_ask is None:
            orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
            if orderbook:
                bids = orderbook.get("bids", [])
                asks = orderbook.get("asks", [])
                if bids and asks:
                    best_bid = float(bids[0].get("price", 0))
                    best_ask = float(asks[0].get("price", 0))
        
        if best_bid is None or best_ask is None:
            return None
        
        mid_price = (best_bid + best_ask) / 2
        if mid_price == 0:
            return None
        
        # Simular ejecución de orden de capacidad completa
        # Calcular precio promedio de ejecución
        orderbook = self.market_state.get("orderbook_snapshot") or self.market_state.get("orderbook")
        if not orderbook:
            return None
        
        bids = orderbook.get("bids", [])
        if not bids:
            return None
        
        total_cost = 0.0
        total_contracts = 0.0
        remaining_capital = capacity
        
        for bid in bids:
            if remaining_capital <= 0:
                break
            
            price = float(bid.get("price", 0))
            size = float(bid.get("size", 0))
            
            if price <= 0 or size <= 0:
                continue
            
            available_capital = price * size
            
            capital_to_use = min(remaining_capital, available_capital)
            contracts = capital_to_use / price
            
            total_cost += capital_to_use
            total_contracts += contracts
            remaining_capital -= capital_to_use
        
        if total_contracts == 0:
            return None
        
        avg_execution_price = total_cost / total_contracts
        slippage = (avg_execution_price - mid_price) / mid_price
        
        return slippage
    
    # ========== Métodos auxiliares (memoización) ==========
    
    def _get_price_history_processed(self) -> Optional[List[Dict[str, Any]]]:
        """
        ⚠️ ALERTA DE COMBATE: Procesa historial de precios una sola vez (memoizado).
        
        Tanto price_drift como tw_volatility necesitan el historial procesado.
        """
        return self.memoize(
            "price_history_processed",
            self._process_price_history
        )
    
    def _process_price_history(self) -> Optional[List[Dict[str, Any]]]:
        """Procesa el historial de precios (filtrado, ordenado, validado)."""
        if not self.market_state:
            return None
        
        price_history = self.market_state.get("price_history", [])
        if not price_history:
            return None
        
        # Validar freshness del historial
        if not self.check_data_freshness(
            self.market_state,
            timestamp_key="price_history_last_update",
            max_age_ms=10000
        ):
            return None
        
        # Procesar: filtrar, ordenar por timestamp, validar
        processed = []
        for entry in price_history:
            price = entry.get("price")
            timestamp = entry.get("timestamp")
            
            if price is None or timestamp is None:
                continue
            
            try:
                price = float(price)
            except (ValueError, TypeError):
                continue
            
            processed.append({
                "price": price,
                "timestamp": timestamp,
                "volume": float(entry.get("volume", 0))
            })
        
        # Ordenar por timestamp
        try:
            processed.sort(key=lambda x: self._parse_timestamp_for_sort(x["timestamp"]))
        except Exception:
            logger.warning("Error sorting price history by timestamp")
            return None
        
        return processed
    
    def _parse_timestamp_for_sort(self, timestamp: Any) -> float:
        """Convierte timestamp a float para ordenamiento."""
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.timestamp()
            except (ValueError, AttributeError):
                return 0.0
        if isinstance(timestamp, datetime):
            return timestamp.timestamp()
        return 0.0

