"""
Proveedor de señales para estrategias de Arbitraje/Surebet.

Implementa los 10 indicadores de arbitraje con validación de freshness y confiabilidad.
"""
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
import logging
import statistics

from app.core.strategy_engine.indicators.base import SignalProvider

logger = logging.getLogger(__name__)


class ArbitrageProvider(SignalProvider):
    """
    Proveedor de señales para estrategias de Arbitraje/Surebet.
    
    Implementa los 10 indicadores:
    - net_arb_gap: Diferencia neta de precio entre plataformas después de fees
    - latency_delta: Diferencia de latencia entre obtener precio de Polymarket vs fuente externa
    - liquidity_match: Proporción de liquidez disponible en ambas plataformas
    - hedge_slippage: Slippage estimado al hacer hedge en la segunda plataforma
    - sync_status: Estado de sincronización entre plataformas
    - price_correlation: Correlación de precios entre plataformas
    - fill_probability: Probabilidad estimada de que ambas órdenes se ejecuten
    - rejection_risk: Riesgo de que una orden sea rechazada
    - gas_impact: Impacto de costos de gas en la rentabilidad
    - arb_persistence: Persistencia de la oportunidad de arbitraje
    """
    
    def validate_data(self) -> bool:
        """
        Valida que existan market_state y external_data.
        
        Returns:
            True si los datos necesarios están disponibles
        """
        return (
            self.market_state is not None and
            self.external_data is not None
        )
    
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula todos los indicadores de arbitraje.
        
        ⚠️ ALERTA DE COMBATE: Verifica confiabilidad de datos externos antes de calcular.
        Si latency_delta > 2000ms o API externa falla, retorna señales con flag unreliable.
        
        Returns:
            Dict con todos los indicadores calculados (None si no se puede calcular)
        """
        if not self.validate_data():
            return self._empty_signals()
        
        # Limpiar cache al inicio de cada cálculo (nuevo tick)
        self.clear_memo_cache()
        
        # ⚠️ Verificar confiabilidad de datos externos
        if not self._check_reliability():
            # Forzar estado unreliable: todos los indicadores críticos en None
            signals = self._empty_signals()
            signals["unreliable"] = 1.0  # Flag especial para indicar datos no confiables
            logger.warning("External data is unreliable, forcing unreliable state")
            return signals
        
        return {
            "net_arb_gap": self._calculate_net_arb_gap(),
            "latency_delta": self._calculate_latency_delta(),
            "liquidity_match": self._calculate_liquidity_match(),
            "hedge_slippage": self._calculate_hedge_slippage(),
            "sync_status": self._calculate_sync_status(),
            "price_correlation": self._calculate_price_correlation(),
            "fill_probability": self._calculate_fill_probability(),
            "rejection_risk": self._calculate_rejection_risk(),
            "gas_impact": self._calculate_gas_impact(),
            "arb_persistence": self._calculate_arb_persistence(),
        }
    
    def _empty_signals(self) -> Dict[str, Optional[float]]:
        """
        Retorna dict con todas las señales en None.
        
        Returns:
            Dict con todas las claves de indicadores en None
        """
        return {key: None for key in [
            "net_arb_gap", "latency_delta", "liquidity_match",
            "hedge_slippage", "sync_status", "price_correlation",
            "fill_probability", "rejection_risk", "gas_impact", "arb_persistence",
            "unreliable"  # Flag especial para indicar datos no confiables
        ]}
    
    def _check_reliability(self) -> bool:
        """
        ⚠️ ALERTA DE COMBATE: Verifica si los datos externos son confiables.
        
        Regla de Seguridad: Si la API externa falla o latency_delta > 2000ms,
        los datos se consideran no confiables.
        
        Returns:
            True si los datos son confiables, False en caso contrario
        """
        if not self.external_data:
            return False
        
        # Verificar freshness del external_data (max 30 segundos)
        if not self.check_data_freshness(self.external_data, max_age_ms=30000):
            logger.warning("external_data is stale, considering unreliable")
            return False
        
        # Calcular latency_delta (puede ser None si no hay timestamps)
        latency_delta = self._calculate_latency_delta()
        if latency_delta is not None and latency_delta > 2000:
            logger.warning(f"latency_delta ({latency_delta}ms) exceeds 2000ms threshold, considering unreliable")
            return False
        
        return True
    
    # ========== Métodos de cálculo de indicadores ==========
    
    def _calculate_net_arb_gap(self) -> Optional[float]:
        """
        Calcula net_arb_gap: Diferencia neta de precio entre plataformas después de fees.
        
        Fórmula: (price_external - price_polymarket - total_fees) / price_polymarket
        Rango: [-∞, ∞] donde > 0.02 (2%) = oportunidad viable
        """
        if not self.market_state or not self.external_data:
            return None
        
        # Validar freshness
        if not self.check_data_freshness(self.market_state, max_age_ms=5000):
            return None
        
        price_polymarket = self.market_state.get("last_price")
        if price_polymarket is None:
            return None
        
        # Intentar obtener precio externo (puede estar en diferentes campos)
        price_external = (
            self.external_data.get("pinnacle_price") or
            self.external_data.get("bet365_price") or
            self.external_data.get("external_price") or
            self.external_data.get("price")
        )
        
        if price_external is None:
            return None
        
        # Obtener fees (default: 0.02 = 2%)
        total_fees = self.external_data.get("total_fees", 0.02)
        
        if price_polymarket == 0:
            return None
        
        net_gap = (price_external - price_polymarket - total_fees) / price_polymarket
        return net_gap
    
    def _calculate_latency_delta(self) -> Optional[float]:
        """
        Calcula latency_delta: Diferencia de latencia entre obtener precio de Polymarket vs fuente externa.
        
        Fórmula: latency_external - latency_polymarket (en milisegundos)
        Rango: [0, ∞] donde < 500ms = aceptable, > 2000ms = unreliable
        """
        if not self.market_state or not self.external_data:
            return None
        
        # Obtener timestamps de última actualización
        market_timestamp = self.market_state.get("last_update")
        external_timestamp = self.external_data.get("last_update")
        
        if not market_timestamp or not external_timestamp:
            return None
        
        # Parsear timestamps
        market_time = self._parse_timestamp(market_timestamp)
        external_time = self._parse_timestamp(external_timestamp)
        
        if not market_time or not external_time:
            return None
        
        # Calcular diferencia en milisegundos
        now = datetime.now(timezone.utc)
        market_latency = (now - market_time).total_seconds() * 1000
        external_latency = (now - external_time).total_seconds() * 1000
        
        latency_delta = external_latency - market_latency
        return latency_delta
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parsea timestamp a datetime."""
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, (int, float)):
            if timestamp > 1e10:  # Milisegundos
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:  # Segundos
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
        return None
    
    def _calculate_liquidity_match(self) -> Optional[float]:
        """
        Calcula liquidity_match: Proporción de liquidez disponible en ambas plataformas.
        
        Fórmula: min(liquidity_polymarket, liquidity_external) / order_size
        Rango: [0, 1] donde > 0.8 = suficiente liquidez
        """
        if not self.market_state or not self.external_data:
            return None
        
        liquidity_polymarket = self.market_state.get("liquidity") or self.market_state.get("total_liquidity", 0)
        liquidity_external = self.external_data.get("liquidity") or self.external_data.get("total_liquidity", 0)
        
        if liquidity_polymarket == 0 or liquidity_external == 0:
            return None
        
        # Obtener tamaño de orden objetivo (default: 1000)
        order_size = self.risk_state.get("target_order_size", 1000) if self.risk_state else 1000
        
        if order_size == 0:
            return None
        
        min_liquidity = min(liquidity_polymarket, liquidity_external)
        match = min_liquidity / order_size
        
        # Clamp a [0, 1]
        return min(match, 1.0)
    
    def _calculate_hedge_slippage(self) -> Optional[float]:
        """
        Calcula hedge_slippage: Slippage estimado al hacer hedge en la segunda plataforma.
        
        Fórmula: (hedge_execution_price - hedge_mid_price) / hedge_mid_price
        Rango: [-∞, ∞]
        """
        if not self.external_data:
            return None
        
        # Obtener orderbook externo
        external_orderbook = self.external_data.get("orderbook") or self.external_data.get("orderbook_snapshot")
        if not external_orderbook:
            return None
        
        bids = external_orderbook.get("bids", [])
        asks = external_orderbook.get("asks", [])
        
        if not bids or not asks:
            return None
        
        best_bid = float(bids[0].get("price", 0))
        best_ask = float(asks[0].get("price", 0))
        
        if best_bid == 0 or best_ask == 0:
            return None
        
        mid_price = (best_bid + best_ask) / 2
        
        # Calcular precio de ejecución teórico para orden de referencia
        reference_size = 1000
        execution_price = best_ask  # Asumimos compra (peor caso)
        
        slippage = (execution_price - mid_price) / mid_price
        return slippage
    
    def _calculate_sync_status(self) -> Optional[float]:
        """
        Calcula sync_status: Estado de sincronización entre plataformas.
        
        Basado en correlación de precios recientes.
        Rango: [0, 1] donde 1 = sincronizado
        """
        # Usar price_correlation como base para sync_status
        correlation = self._calculate_price_correlation()
        if correlation is None:
            return None
        
        # Convertir correlación [-1, 1] a sync_status [0, 1]
        # Correlación > 0.9 = sync_status alto
        if correlation > 0.9:
            return 1.0
        elif correlation > 0.7:
            return 0.7
        elif correlation > 0.5:
            return 0.5
        elif correlation > 0:
            return 0.3
        else:
            return 0.0
    
    def _calculate_price_correlation(self) -> Optional[float]:
        """
        Calcula price_correlation: Correlación de precios entre plataformas.
        
        Fórmula: Coeficiente de correlación de Pearson
        Rango: [-1, 1] donde > 0.9 = alta correlación
        """
        if not self.market_state or not self.external_data:
            return None
        
        # Obtener historiales de precios
        polymarket_history = self.market_state.get("price_history", [])
        external_history = self.external_data.get("price_history", [])
        
        if not polymarket_history or not external_history:
            return None
        
        # Procesar historiales para obtener listas de precios sincronizados
        # Simplificado: usar últimos N precios
        n_samples = min(len(polymarket_history), len(external_history), 20)
        if n_samples < 2:
            return None
        
        polymarket_prices = [
            float(entry.get("price", 0))
            for entry in polymarket_history[-n_samples:]
            if entry.get("price") is not None
        ]
        external_prices = [
            float(entry.get("price", 0))
            for entry in external_history[-n_samples:]
            if entry.get("price") is not None
        ]
        
        if len(polymarket_prices) != len(external_prices) or len(polymarket_prices) < 2:
            return None
        
        # Calcular correlación de Pearson
        try:
            correlation = statistics.correlation(polymarket_prices, external_prices)
            return correlation
        except (statistics.StatisticsError, ValueError):
            return None
    
    def _calculate_fill_probability(self) -> Optional[float]:
        """
        Calcula fill_probability: Probabilidad estimada de que ambas órdenes se ejecuten.
        
        Fórmula: min(fill_prob_polymarket, fill_prob_external)
        Rango: [0, 1]
        """
        if not self.market_state or not self.external_data:
            return None
        
        # Obtener probabilidades de fill desde historial o estimación
        fill_prob_polymarket = self.market_state.get("fill_probability", 0.95)  # Default optimista
        fill_prob_external = self.external_data.get("fill_probability", 0.90)  # Default optimista
        
        # Si hay historial de ejecuciones, calcular desde ahí
        polymarket_fill_rate = self.market_state.get("fill_rate")
        external_fill_rate = self.external_data.get("fill_rate")
        
        if polymarket_fill_rate is not None:
            fill_prob_polymarket = polymarket_fill_rate
        if external_fill_rate is not None:
            fill_prob_external = external_fill_rate
        
        fill_probability = min(fill_prob_polymarket, fill_prob_external)
        return fill_probability
    
    def _calculate_rejection_risk(self) -> Optional[float]:
        """
        Calcula rejection_risk: Riesgo de que una orden sea rechazada.
        
        Basado en historial de rechazos y políticas de la plataforma.
        Rango: [0, 1] donde 0 = sin riesgo, 1 = alto riesgo
        """
        if not self.external_data:
            return None
        
        # Obtener historial de rechazos
        rejection_history = self.external_data.get("rejection_history", [])
        rejection_rate = self.external_data.get("rejection_rate")
        
        if rejection_rate is not None:
            return float(rejection_rate)
        
        # Calcular desde historial si está disponible
        if rejection_history:
            total_orders = len(rejection_history)
            rejected = sum(1 for order in rejection_history if order.get("status") == "REJECTED")
            if total_orders > 0:
                return rejected / total_orders
        
        # Default: bajo riesgo si no hay historial
        return 0.05  # 5% de riesgo por defecto
    
    def _calculate_gas_impact(self) -> Optional[float]:
        """
        Calcula gas_impact: Impacto de costos de gas en la rentabilidad.
        
        Fórmula: gas_cost / order_size
        Rango: [0, ∞] donde valores altos = impacto negativo
        """
        if not self.market_state:
            return None
        
        # Obtener estimación de gas
        gas_estimate = self.market_state.get("gas_estimate") or self.external_data.get("gas_estimate") if self.external_data else None
        gas_price = self.market_state.get("gas_price") or self.external_data.get("gas_price") if self.external_data else None
        
        if gas_estimate is None or gas_price is None:
            # Si no hay datos de gas, retornar None (no aplica)
            return None
        
        gas_cost = gas_estimate * gas_price
        
        # Obtener tamaño de orden
        order_size = self.risk_state.get("target_order_size", 1000) if self.risk_state else 1000
        
        if order_size == 0:
            return None
        
        impact = gas_cost / order_size
        return impact
    
    def _calculate_arb_persistence(self) -> Optional[float]:
        """
        Calcula arb_persistence: Persistencia de la oportunidad de arbitraje.
        
        Fórmula: time_opportunity_exists / max_expected_duration
        Rango: [0, 1] donde > 0.5 = oportunidad persistente
        """
        if not self.external_data:
            return None
        
        # Obtener timestamp de primera detección
        first_detected = self.external_data.get("arb_opportunity_first_seen")
        if not first_detected:
            return None
        
        first_detected_time = self._parse_timestamp(first_detected)
        if not first_detected_time:
            return None
        
        # Calcular tiempo transcurrido
        now = datetime.now(timezone.utc)
        time_elapsed = (now - first_detected_time).total_seconds()
        
        # Duración máxima esperada (default: 5 minutos = 300 segundos)
        max_expected_duration = self.external_data.get("max_arb_duration_seconds", 300)
        
        if max_expected_duration == 0:
            return None
        
        persistence = time_elapsed / max_expected_duration
        
        # Clamp a [0, 1]
        return min(persistence, 1.0)

