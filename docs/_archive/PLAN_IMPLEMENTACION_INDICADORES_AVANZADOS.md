# Plan de Implementación: Motor de Indicadores Avanzados (Signals)

**Fecha**: 2025-12-21  
**Versión**: 1.0  
**Objetivo**: Implementar un motor modular de indicadores avanzados que soporte múltiples tipos de estrategias (Liquidity Provider y Surebet/Arbitrage) con integración completa en backend y frontend.

---

## 📋 Índice

1. [Fase 1: Estructura Base del Motor de Indicadores](#fase-1-estructura-base-del-motor-de-indicadores)
2. [Fase 2: Implementación de Indicadores para Liquidity Provider](#fase-2-implementación-de-indicadores-para-liquidity-provider)
3. [Fase 3: Integración en Decision Engine](#fase-3-integración-en-decision-engine)
4. [Fase 4: Actualización de Estrategias JSON](#fase-4-actualización-de-estrategias-json)
5. [Fase 5: Implementación de Indicadores para Arbitrage/Surebet](#fase-5-implementación-de-indicadores-para-arbitragesurebet)
6. [Fase 6: Integración Frontend - SignalsMonitor](#fase-6-integración-frontend---signalsmonitor)
7. [Fase 7: Trazabilidad y Seguridad](#fase-7-trazabilidad-y-seguridad)
8. [Fase 8: Terminal de Control de Elite](#fase-8-terminal-de-control-de-elite)
9. [Fase 9: Testing y Validación](#fase-9-testing-y-validación)

---

## Fase 1: Estructura Base del Motor de Indicadores

### 1.1 Crear Estructura de Directorios

**Ubicación**: `backend/app/core/strategy_engine/indicators/`

**Archivos a crear**:
- `__init__.py` - Exporta clases principales
- `base.py` - Clase base abstracta `SignalProvider`
- `factory.py` - Factoría para instanciar proveedores
- `liquidity_provider.py` - Implementación para Liquidity Provider
- `arbitrage_provider.py` - Estructura base para Surebet/Arbitrage

### 1.2 Implementar Clase Base Abstracta (`base.py`)

**Responsabilidades**:
- Definir interfaz común para todos los proveedores de señales
- Método abstracto `calculate_all()` que retorna `Dict[str, Optional[float]]`
- Método abstracto `validate_data()` para verificar datos necesarios
- Propiedades para acceder a `market_state`, `event_state`, `external_data`, `risk_state`
- **⚠️ CRÍTICO**: Validación de freshness de datos (Stale Data Protection)
- **⚠️ CRÍTICO**: Sistema de memoización para evitar cálculos redundantes

**Estructura**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SignalProvider(ABC):
    """Clase base abstracta para proveedores de señales."""
    
    def __init__(self, context: GraphExecutionContext):
        self.context = context
        self._collected_state = context.collected_state
        self._memo_cache: Dict[str, Any] = {}  # Cache para memoización
        self._memo_timestamps: Dict[str, datetime] = {}  # Timestamps de cache
    
    @property
    def market_state(self) -> Optional[Dict[str, Any]]:
        return self._collected_state.get("market_state")
    
    @property
    def event_state(self) -> Optional[Dict[str, Any]]:
        return self._collected_state.get("event_state")
    
    @property
    def external_data(self) -> Optional[Dict[str, Any]]:
        return self._collected_state.get("external_data")
    
    @property
    def risk_state(self) -> Optional[Dict[str, Any]]:
        return self._collected_state.get("risk_state")
    
    def check_data_freshness(
        self, 
        data: Dict[str, Any], 
        timestamp_key: str = "last_update",
        max_age_ms: int = 5000
    ) -> bool:
        """
        ⚠️ ALERTA DE COMBATE: Valida que los datos no sean obsoletos.
        
        Problema: Un indicador puede tener datos, pero si el orderbook es de hace 10 segundos,
        el book_imbalance es peligroso.
        
        Args:
            data: Diccionario con los datos a validar
            timestamp_key: Clave donde está el timestamp (default: "last_update")
            max_age_ms: Edad máxima permitida en milisegundos (default: 5000ms = 5 segundos)
        
        Returns:
            True si los datos son frescos, False si son obsoletos
        """
        if not data:
            return False
        
        timestamp = data.get(timestamp_key)
        if timestamp is None:
            # Si no hay timestamp, asumir que los datos son frescos (compatibilidad)
            # Pero loggear advertencia
            logger.warning(
                f"Data missing timestamp key '{timestamp_key}', assuming fresh",
                extra={"data_keys": list(data.keys())}
            )
            return True
        
        # Convertir timestamp a datetime si es string o número
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return False
        elif isinstance(timestamp, (int, float)):
            # Asumir que es Unix timestamp en segundos o milisegundos
            if timestamp > 1e10:  # Milisegundos
                timestamp = datetime.fromtimestamp(timestamp / 1000)
            else:  # Segundos
                timestamp = datetime.fromtimestamp(timestamp)
        elif not isinstance(timestamp, datetime):
            logger.warning(f"Unknown timestamp type: {type(timestamp)}")
            return False
        
        # Calcular edad
        now = datetime.utcnow()
        if timestamp.tzinfo:
            now = datetime.now(timestamp.tzinfo)
        
        age_ms = (now - timestamp).total_seconds() * 1000
        
        if age_ms > max_age_ms:
            logger.warning(
                f"Data is stale: {age_ms:.0f}ms old (max: {max_age_ms}ms)",
                extra={"age_ms": age_ms, "max_age_ms": max_age_ms}
            )
            return False
        
        return True
    
    def memoize(self, key: str, func: callable, *args, **kwargs) -> Any:
        """
        ⚠️ ALERTA DE COMBATE: Sistema de memoización para evitar cálculos redundantes.
        
        Problema: Si tienes 20 indicadores y cada uno hace cálculos pesados (ej. procesar
        historial de precios), podrías ralentizar el ControlLoop.
        
        Solución: Si price_drift y tw_volatility usan ambos el historial de precios,
        procesar ese historial una sola vez por tick.
        
        Args:
            key: Clave única para el cache
            func: Función a ejecutar (solo si no está en cache)
            *args, **kwargs: Argumentos para la función
        
        Returns:
            Resultado de la función (desde cache o calculado)
        """
        # Verificar si está en cache y es válido
        if key in self._memo_cache:
            # El cache es válido para este tick (mismo contexto)
            return self._memo_cache[key]
        
        # Calcular y guardar en cache
        result = func(*args, **kwargs)
        self._memo_cache[key] = result
        self._memo_timestamps[key] = datetime.utcnow()
        
        return result
    
    def clear_memo_cache(self):
        """Limpia el cache de memoización (útil para testing o reset)."""
        self._memo_cache.clear()
        self._memo_timestamps.clear()
    
    @abstractmethod
    def validate_data(self) -> bool:
        """Valida que los datos necesarios estén disponibles."""
        pass
    
    @abstractmethod
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula todos los indicadores.
        
        Returns:
            Dict con claves de indicadores y valores (None si no se puede calcular)
        """
        pass
```

### 1.3 Implementar Factory (`factory.py`)

**Responsabilidades**:
- Mapear `strategy_type` a clase de proveedor correspondiente
- Instanciar el proveedor correcto según el tipo de estrategia
- Manejar errores si el tipo no está soportado

**Estructura**:
```python
from typing import Dict, Type
from app.core.strategy_engine.indicators.base import SignalProvider
from app.core.strategy_engine.indicators.liquidity_provider import LiquidityProvider
from app.core.strategy_engine.indicators.arbitrage_provider import ArbitrageProvider

_PROVIDER_REGISTRY: Dict[str, Type[SignalProvider]] = {
    "liquidity": LiquidityProvider,
    "liquidity_near_end": LiquidityProvider,  # Alias
    "surebet_arbitrage": ArbitrageProvider,
    "arbitrage": ArbitrageProvider,  # Alias
}

def create_signal_provider(
    strategy_type: str,
    context: GraphExecutionContext
) -> SignalProvider:
    """
    Crea el proveedor de señales apropiado según el strategy_type.
    
    Args:
        strategy_type: Tipo de estrategia ("liquidity", "surebet_arbitrage", etc.)
        context: Contexto de ejecución del grafo
    
    Returns:
        Instancia del proveedor correspondiente
    
    Raises:
        ValueError: Si el strategy_type no está soportado
    """
    provider_class = _PROVIDER_REGISTRY.get(strategy_type)
    if not provider_class:
        raise ValueError(f"Unsupported strategy_type: {strategy_type}")
    
    return provider_class(context)
```

### 1.4 Crear Estructura Base para ArbitrageProvider (`arbitrage_provider.py`)

**Responsabilidades**:
- Heredar de `SignalProvider`
- Implementar estructura base con método `calculate_all()` que retorna dict vacío
- Preparar para futura implementación de indicadores de arbitraje

**Estructura**:
```python
from typing import Dict, Optional
from app.core.strategy_engine.indicators.base import SignalProvider

class ArbitrageProvider(SignalProvider):
    """Proveedor de señales para estrategias de Arbitraje/Surebet."""
    
    def validate_data(self) -> bool:
        """Valida que existan market_state y external_data."""
        return (
            self.market_state is not None and
            self.external_data is not None
        )
    
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula todos los indicadores de arbitraje.
        
        TODO: Implementar los 10 indicadores:
        - net_arb_gap
        - latency_delta
        - liquidity_match
        - hedge_slippage
        - sync_status
        - price_correlation
        - fill_probability
        - rejection_risk
        - gas_impact
        - arb_persistence
        """
        if not self.validate_data():
            return self._empty_signals()
        
        # Estructura preparada para implementación futura
        return {
            "net_arb_gap": None,
            "latency_delta": None,
            "liquidity_match": None,
            "hedge_slippage": None,
            "sync_status": None,
            "price_correlation": None,
            "fill_probability": None,
            "rejection_risk": None,
            "gas_impact": None,
            "arb_persistence": None,
        }
    
    def _empty_signals(self) -> Dict[str, Optional[float]]:
        """Retorna dict con todas las señales en None."""
        return {key: None for key in [
            "net_arb_gap", "latency_delta", "liquidity_match",
            "hedge_slippage", "sync_status", "price_correlation",
            "fill_probability", "rejection_risk", "gas_impact", "arb_persistence"
        ]}
```

---

## Fase 2: Implementación de Indicadores para Liquidity Provider

### 2.1 Implementar LiquidityProvider (`liquidity_provider.py`)

**Responsabilidades**:
- Implementar los 10 indicadores técnicos para estrategias de liquidez
- Implementar los 4 nuevos indicadores de rentabilidad (Quant Engine)
- Consumir datos de `polymarket_payload` y `StateCache`
- Manejar casos donde faltan datos (retornar `None`)

### 2.2 Indicadores Técnicos a Implementar (Mantenidos)

#### 2.2.1 `book_imbalance`
**Descripción**: Mide el desequilibrio entre ofertas y demandas en el orderbook.  
**Fórmula**: `(total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)`  
**Rango**: [-1, 1] donde 0 = balance perfecto  
**Fuente de datos**: `market_state.orderbook` o `polymarket_payload.orderbook`

#### 2.2.2 `toxic_flow`
**Descripción**: Mide la proporción de trades que se ejecutan en contra de nuestra posición.  
**Fórmula**: `trades_against_us / total_trades` en ventana temporal  
**Rango**: [0, 1] donde 0 = flujo favorable, 1 = flujo tóxico  
**Fuente de datos**: `market_state.recent_trades` o historial de trades

#### 2.2.3 `inventory_skew` ⚠️ **CRÍTICO - ALERTA DE COMBATE**
**Descripción**: Mide el desbalance de nuestra posición actual vs posición objetivo.  
**Fórmula**: `abs(current_position - target_position) / max_position`  
**Rango**: [0, 1] donde 0 = posición óptima, 1 = desbalance máximo  
**Fuente de datos**: 
- `risk_state.current_position` (posición actual)
- `risk_state.target_position` (posición objetivo)
- `risk_state.max_position` (límite máximo)

**⚠️ ALERTA CRÍTICA**: Este indicador es el más delicado porque depende de tu estado interno, no del mercado.

**Problema**: Asegúrate de que el `risk_state` que recibe el nodo esté sincronizado con la última orden ejecutada. Si hay una orden en vuelo (pending), el skew podría ser erróneo.

**Solución**:
1. **Sincronización con ExecutionEngine**: El `risk_state` debe incluir órdenes pendientes:
   ```python
   current_position = risk_state.get("current_position", 0)
   pending_orders = risk_state.get("pending_orders", [])
   
   # Ajustar posición con órdenes pendientes
   pending_position_delta = sum(
       order.get("size", 0) * (1 if order.get("side") == "BUY" else -1)
       for order in pending_orders
       if order.get("status") in ["PENDING", "SUBMITTED"]
   )
   
   effective_position = current_position + pending_position_delta
   ```

2. **Validación de Freshness**: Verificar que `risk_state.last_update` sea reciente (< 2 segundos)

3. **Fallback Seguro**: Si no hay `risk_state` o está obsoleto, retornar `None` en lugar de calcular con datos incorrectos

#### 2.2.4 `price_drift`
**Descripción**: Mide el cambio de precio en una ventana temporal.  
**Fórmula**: `(current_price - price_N_minutes_ago) / price_N_minutes_ago`  
**Rango**: [-∞, ∞] (normalmente [-0.1, 0.1] para cambios del 10%)  
**Fuente de datos**: `market_state.price_history` o `market_state.last_price` con timestamp

#### 2.2.5 `spread_elasticity`
**Descripción**: Mide qué tan rápido cambia el spread cuando hay presión de compra/venta.  
**Fórmula**: `delta_spread / delta_volume`  
**Rango**: [0, ∞] donde valores altos = spread inelástico (malo)  
**Fuente de datos**: `market_state.spread` y `market_state.volume`

#### 2.2.6 `cancel_rate`
**Descripción**: Proporción de órdenes canceladas vs ejecutadas.  
**Fórmula**: `cancelled_orders / (executed_orders + cancelled_orders)`  
**Rango**: [0, 1] donde 0 = todas ejecutadas, 1 = todas canceladas  
**Fuente de datos**: Historial de órdenes desde `risk_state.order_history` o `external_data.order_status`

#### 2.2.7 `rel_liquidity`
**Descripción**: Liquidez relativa vs promedio histórico.  
**Fórmula**: `current_liquidity / average_liquidity_24h`  
**Rango**: [0, ∞] donde 1 = liquidez normal  
**Fuente de datos**: `market_state.liquidity` y `market_state.liquidity_history`

#### 2.2.8 `tw_volatility` (Time-Weighted Volatility)
**Descripción**: Volatilidad ponderada por tiempo en ventana reciente.  
**Fórmula**: Desviación estándar de precios ponderada por tiempo  
**Rango**: [0, ∞]  
**Fuente de datos**: `market_state.price_history` con timestamps

#### 2.2.9 `res_gap` (Resolution Gap)
**Descripción**: Diferencia entre precio de mercado y precio esperado post-resolución.  
**Fórmula**: `abs(market_price - expected_resolution_price)`  
**Rango**: [0, 1]  
**Fuente de datos**: 
- `market_state.last_price`
- `external_data.expected_resolution_price` o `event_state.confirmed_outcome_probability`

#### 2.2.10 `slippage_impact`
**Descripción**: Impacto estimado de slippage para una orden de tamaño estándar.  
**Fórmula**: `(execution_price - mid_price) / mid_price` para orden de referencia  
**Rango**: [-∞, ∞] (normalmente [-0.05, 0.05] para 5% de slippage)  
**Fuente de datos**: `market_state.orderbook` para calcular precio de ejecución teórico

### 2.3 Nuevos Indicadores de Rentabilidad (Quant Engine) 🚀

**Objetivo**: Calcular la rentabilidad real basada en el análisis del libro de órdenes (Trade Book Analysis).

#### 2.3.1 `expected_roi_at_depth`
**Descripción**: Función que recorre el libro de órdenes y calcula el ROI medio ponderado si compráramos $X$ cantidad de contratos.  
**Fórmula**: 
```
ROI_medio = Σ(roi_nivel_i * capital_nivel_i) / Σ(capital_nivel_i)
donde roi_nivel_i = (1.0 - precio_nivel_i) / precio_nivel_i
```
**Rango**: [0, ∞] donde > 0.06 (6%) = rentable  
**Fuente de datos**: 
- `market_state.orderbook_snapshot.bids` (para compras)
- `event_state.close_time` o `event_state.resolution_time` para calcular tiempo hasta resolución
- `market_state.last_price` como precio de referencia

**Implementación**:
```python
def _calculate_expected_roi_at_depth(self, capital_amount: float) -> Optional[float]:
    """
    Calcula ROI medio ponderado al comprar capital_amount de contratos.
    
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
    
    # Obtener precio de resolución esperado (1.0 para YES, 0.0 para NO)
    # Simplificado: asumimos que el evento se resuelve a 1.0 si gana
    resolution_price = 1.0  # TODO: Obtener desde event_state.confirmed_outcome_probability
    
    total_roi_weighted = 0.0
    total_capital_used = 0.0
    remaining_capital = capital_amount
    
    # Recorrer el libro desde el mejor precio hacia abajo
    for bid in bids:
        if remaining_capital <= 0:
            break
        
        price = float(bid.get("price", 0))
        size = float(bid.get("size", 0))
        available_capital = price * size  # Capital necesario para comprar este nivel
        
        # Calcular cuánto capital usar de este nivel
        capital_to_use = min(remaining_capital, available_capital)
        contracts_to_buy = capital_to_use / price
        
        # Calcular ROI de este nivel
        roi_level = (resolution_price - price) / price
        
        # Acumular ROI ponderado
        total_roi_weighted += roi_level * capital_to_use
        total_capital_used += capital_to_use
        remaining_capital -= capital_to_use
    
    if total_capital_used == 0:
        return None
    
    expected_roi = total_roi_weighted / total_capital_used
    return expected_roi
```

#### 2.3.2 `capital_absorption_capacity`
**Descripción**: Cantidad máxima de capital (hasta 100k) que se puede desplegar en un evento antes de que el ROI caiga por debajo del umbral (ej. 6%).  
**Fórmula**: Búsqueda binaria o iterativa para encontrar el máximo capital donde `expected_roi_at_depth(capital) >= roi_threshold`  
**Rango**: [0, 100000] (en USDC)  
**Fuente de datos**: 
- `expected_roi_at_depth()` (calculado internamente)
- `risk_state.max_capital_per_event` o configuración de estrategia

**Implementación**:
```python
def _calculate_capital_absorption_capacity(self, roi_threshold: float = 0.06) -> Optional[float]:
    """
    Calcula capacidad máxima de absorción manteniendo ROI >= threshold.
    
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
    
    while high - low > tolerance:
        mid = (low + high) / 2
        roi = self._calculate_expected_roi_at_depth(mid)
        
        if roi is None:
            break
        
        if roi >= roi_threshold:
            best_capacity = mid
            low = mid
        else:
            high = mid
    
    return best_capacity if best_capacity > 0 else None
```

#### 2.3.3 `time_value_score`
**Descripción**: Un ratio de eficiencia que prioriza ganancias rápidas: `ROI Proyectado / Tiempo hasta Resolución`.  
**Fórmula**: `expected_roi / time_to_resolution_minutes`  
**Rango**: [0, ∞] donde valores altos = mejor eficiencia  
**Fuente de datos**: 
- `expected_roi_at_depth()` (usando capital_absorption_capacity)
- `event_state.close_time` o `event_state.resolution_time`
- `datetime.utcnow()` para calcular tiempo restante

**Implementación**:
```python
def _calculate_time_value_score(self) -> Optional[float]:
    """
    Calcula score de eficiencia tiempo-valor.
    
    Returns:
        Score de eficiencia (ROI por minuto)
    """
    if not self.event_state:
        return None
    
    # Calcular tiempo hasta resolución
    close_time = self.event_state.get("close_time")
    if not close_time:
        return None
    
    if isinstance(close_time, str):
        close_time = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
    
    time_remaining = (close_time - datetime.utcnow()).total_seconds() / 60  # En minutos
    if time_remaining <= 0:
        return None
    
    # Obtener ROI esperado usando capacidad de absorción
    capacity = self._calculate_capital_absorption_capacity()
    if capacity is None or capacity == 0:
        return None
    
    expected_roi = self._calculate_expected_roi_at_depth(capacity)
    if expected_roi is None:
        return None
    
    time_value_score = expected_roi / time_remaining
    return time_value_score
```

#### 2.3.4 `slippage_impact_100k`
**Descripción**: Cálculo del impacto en el precio al ejecutar órdenes de gran tamaño basadas en el balance disponible (100k).  
**Fórmula**: Similar a `slippage_impact` pero calculado para el tamaño completo de `capital_absorption_capacity`  
**Rango**: [-∞, ∞] (normalmente [-0.01, 0.01] para 1% de slippage)  
**Fuente de datos**: 
- `market_state.orderbook_snapshot.bids`
- `capital_absorption_capacity()` para obtener tamaño de orden
- `market_state.last_price` como precio de referencia

**Implementación**:
```python
def _calculate_slippage_impact_100k(self) -> Optional[float]:
    """
    Calcula impacto de slippage para orden de gran tamaño (basada en balance disponible).
    
    Returns:
        Impacto de slippage como ratio (ej. 0.004 = 0.4%)
    """
    if not self.market_state:
        return None
    
    # Obtener capacidad de absorción (tamaño de orden)
    capacity = self._calculate_capital_absorption_capacity()
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
```

### 2.4 Integración de Indicadores de Rentabilidad en LiquidityProvider

**Modificación en `calculate_all()`**:
```python
def calculate_all(self) -> Dict[str, Optional[float]]:
    """Calcula todos los indicadores (técnicos + rentabilidad)."""
    if not self.validate_data():
        return self._empty_signals()
    
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
    
    # Indicadores de rentabilidad (nuevos)
    roi_threshold = self.risk_state.get("min_roi_threshold", 0.06) if self.risk_state else 0.06
    capacity = self._calculate_capital_absorption_capacity(roi_threshold)
    
    profitability_signals = {
        "expected_roi_at_depth": self._calculate_expected_roi_at_depth(capacity) if capacity else None,
        "capital_absorption_capacity": capacity,
        "time_value_score": self._calculate_time_value_score(),
        "slippage_impact_100k": self._calculate_slippage_impact_100k(),
    }
    
    return {**technical_signals, **profitability_signals}
```

### 2.3 Estructura de Implementación con Memoización

```python
from typing import Dict, Optional, List
from app.core.strategy_engine.indicators.base import SignalProvider

class LiquidityProvider(SignalProvider):
    """Proveedor de señales para estrategias de Liquidity Provider."""
    
    def validate_data(self) -> bool:
        """Valida que exista market_state mínimo."""
        return self.market_state is not None
    
    def calculate_all(self) -> Dict[str, Optional[float]]:
        """
        Calcula los 10 indicadores de liquidez.
        
        ⚠️ ALERTA DE COMBATE: Usa memoización para evitar cálculos redundantes.
        """
        if not self.validate_data():
            return self._empty_signals()
        
        # Limpiar cache al inicio de cada cálculo (nuevo tick)
        self.clear_memo_cache()
        
        return {
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
    
    def _get_price_history_processed(self) -> Optional[List[Dict[str, Any]]]:
        """
        ⚠️ ALERTA DE COMBATE: Procesa historial de precios una sola vez.
        
        Tanto price_drift como tw_volatility necesitan el historial procesado.
        Usar memoización para calcularlo una sola vez.
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
        processed = [
            {
                "price": entry.get("price"),
                "timestamp": entry.get("timestamp"),
                "volume": entry.get("volume", 0)
            }
            for entry in price_history
            if entry.get("price") is not None and entry.get("timestamp") is not None
        ]
        
        # Ordenar por timestamp
        processed.sort(key=lambda x: x["timestamp"])
        
        return processed
    
    def _calculate_book_imbalance(self) -> Optional[float]:
        """
        Calcula book_imbalance con validación de freshness.
        """
        if not self.market_state:
            return None
        
        # ⚠️ Validar freshness
        if not self.check_data_freshness(self.market_state, max_age_ms=5000):
            return None
        
        orderbook = self.market_state.get("orderbook")
        if not orderbook:
            return None
        
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return None
        
        total_bid_volume = sum(bid.get("size", 0) for bid in bids)
        total_ask_volume = sum(ask.get("size", 0) for ask in asks)
        
        if total_bid_volume + total_ask_volume == 0:
            return None
        
        return (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
    
    def _calculate_price_drift(self) -> Optional[float]:
        """
        Calcula price_drift usando historial procesado (memoizado).
        """
        price_history = self._get_price_history_processed()
        if not price_history or len(price_history) < 2:
            return None
        
        # Usar historial ya procesado (memoizado)
        current_price = price_history[-1]["price"]
        # Precio de hace N minutos (ej. 5 minutos)
        # Buscar en historial procesado
        # ... implementación
        
    def _calculate_tw_volatility(self) -> Optional[float]:
        """
        Calcula tw_volatility usando el mismo historial procesado (memoizado).
        """
        price_history = self._get_price_history_processed()
        if not price_history or len(price_history) < 2:
            return None
        
        # Usar el mismo historial procesado que price_drift
        # ... implementación
    
    def _calculate_inventory_skew(self) -> Optional[float]:
        """
        ⚠️ ALERTA DE COMBATE: Calcula inventory_skew con sincronización de órdenes pendientes.
        """
        if not self.risk_state:
            return None
        
        # ⚠️ Validar freshness del risk_state (crítico para este indicador)
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
            order.get("size", 0) * (1 if order.get("side") == "BUY" else -1)
            for order in pending_orders
            if order.get("status") in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]
        )
        
        effective_position = current_position + pending_position_delta
        
        # Calcular skew
        position_diff = abs(effective_position - target_position)
        skew = position_diff / max_position if max_position > 0 else 1.0
        
        return min(skew, 1.0)  # Clamp a [0, 1]
    
    def _calculate_toxic_flow(self) -> Optional[float]:
        """Calcula toxic_flow."""
        # Implementación...
    
    # ... resto de métodos privados
```

### 2.4 Manejo de Datos Faltantes y Stale Data

**Regla 1 - Datos Faltantes**: Si faltan datos necesarios para calcular un indicador, retornar `None`.  
**Ejemplo**: Si no hay `orderbook`, `book_imbalance` = `None`.  
**Validación**: El evaluador de condiciones debe manejar `None` sin crashear.

**Regla 2 - Stale Data Protection** ⚠️ **ALERTA DE COMBATE**:  
**Problema**: Un indicador puede tener datos, pero si el orderbook es de hace 10 segundos, el `book_imbalance` es peligroso.

**Solución**: En cada cálculo de indicador, validar freshness usando `check_data_freshness()`:

```python
def _calculate_book_imbalance(self) -> Optional[float]:
    """Calcula book_imbalance con validación de freshness."""
    if not self.market_state:
        return None
    
    # ⚠️ Validar que los datos sean frescos
    if not self.check_data_freshness(self.market_state, max_age_ms=5000):
        logger.warning("market_state is stale, skipping book_imbalance calculation")
        return None
    
    orderbook = self.market_state.get("orderbook")
    if not orderbook:
        return None
    
    # ... resto del cálculo
```

**Configuración de max_age_ms por tipo de dato**:
- `market_state.orderbook`: 5000ms (5 segundos) - Datos de mercado cambian rápido
- `market_state.price_history`: 10000ms (10 segundos) - Historial puede ser un poco más viejo
- `risk_state`: 2000ms (2 segundos) - Estado de riesgo debe estar muy actualizado
- `external_data`: 30000ms (30 segundos) - APIs externas pueden tener más latencia

---

## Fase 3: Integración en Decision Engine

### 3.1 Crear Nodo `CalculateIndicatorsNode`

**Ubicación**: `backend/app/core/strategy_engine/nodes/calculate_indicators.py`

**Responsabilidades**:
- Llamar a la factory con `strategy_type` del contexto
- Ejecutar `calculate_all()` del proveedor
- Inyectar resultados en `context.signals`
- Manejar errores y retornar `None` si falla

**Estructura**:
```python
from typing import Dict, Any
from app.core.strategy_engine.nodes.base import GraphNode, SuccessResult
from app.core.strategy_engine.indicators.factory import create_signal_provider

class CalculateIndicatorsNode(GraphNode):
    """
    Nodo que calcula indicadores avanzados (signals).
    
    Config:
        strategy_type: str - Tipo de estrategia ("liquidity", "surebet_arbitrage", etc.)
            Si no se especifica, se lee de context.strategy_type o context.strategy.config
    
    Output:
        context.signals: Dict[str, Optional[float]] - Diccionario con todos los indicadores
    """
    
    async def execute(self) -> SuccessResult:
        """Calcula indicadores e inyecta en context.signals."""
        # Obtener strategy_type desde config o contexto
        strategy_type = self.config.get("strategy_type")
        if not strategy_type:
            # Intentar leer desde contexto
            strategy_type = getattr(self.context, "strategy_type", None)
            if not strategy_type:
                # Leer desde strategy config si está disponible
                if hasattr(self.context, "strategy") and self.context.strategy:
                    strategy_type = self.context.strategy.get("strategy_type", "liquidity")
                else:
                    strategy_type = "liquidity"  # Default
        
        try:
            # Crear proveedor
            provider = create_signal_provider(strategy_type, self.context)
            
            # Calcular indicadores
            signals = provider.calculate_all()
            
            # Inyectar en contexto
            if not hasattr(self.context, "signals"):
                self.context.signals = {}
            self.context.signals.update(signals)
            
            return SuccessResult()
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)
            # En caso de error, inyectar señales vacías (None)
            if not hasattr(self.context, "signals"):
                self.context.signals = {}
            # No fallar el nodo, solo retornar señales vacías
            return SuccessResult()
```

### 3.2 Registrar Nodo en GraphRuntime

**Ubicación**: `backend/app/core/strategy_engine/graph_runtime.py`

**Modificación**:
```python
from app.core.strategy_engine.nodes.calculate_indicators import CalculateIndicatorsNode

def _register_builtin_nodes(self):
    """Registra nodos predefinidos."""
    # ... nodos existentes ...
    self.node_registry["calculate_indicators"] = CalculateIndicatorsNode
```

### 3.3 Actualizar GraphExecutionContext

**Ubicación**: `backend/app/core/strategy_engine/models.py`

**Verificar/Agregar**:
- Atributo `signals: Dict[str, Optional[float]]` en `GraphExecutionContext`
- Inicialización en `__init__` si no existe

---

## Fase 4: Actualización de Estrategias JSON

### 4.1 Actualizar JSON de "Near-Resolution Liquidity Provider"

**Ubicación**: `backend/app/models/strategy_template.py` o archivo JSON de estrategia

**Cambios**:
1. Insertar nodo `compute_signals` después de `collect_state`
2. Actualizar nodo `check_event_finished` con condiciones basadas en señales

**Estructura**:
```json
{
  "decision_graph": {
    "entry_node": "collect_state",
    "nodes": {
      "collect_state": {
        "type": "collect_state",
        "config": {
          "sources": ["market_state", "event_state", "external_data", "risk_state"]
        },
        "next": "compute_signals"
      },
      "compute_signals": {
        "type": "calculate_indicators",
        "config": {
          "strategy_type": "liquidity"
        },
        "next": "check_event_finished"
      },
      "check_event_finished": {
        "type": "edge_and_risk_check",
        "config": {
          "conditions": [
            {
              "field": "event_state.state",
              "operator": "==",
              "value": "FINISHED_CONFIRMED"
            },
            {
              "field": "signals.toxic_flow",
              "operator": "<",
              "value": 0.25
            },
            {
              "field": "signals.book_imbalance",
              "operator": ">=",
              "value": 0.4
            },
            {
              "field": "signals.book_imbalance",
              "operator": "<=",
              "value": 0.6
            },
            {
              "field": "signals.inventory_skew",
              "operator": "<",
              "value": 0.7
            }
          ],
          "logic": "AND"
        },
        "on_true": "check_price_range",
        "on_false": "idle"
      },
      // ... resto de nodos
    }
  }
}
```

### 4.2 Actualizar EdgeAndRiskCheckNode para Soportar `signals.*`

**Ubicación**: `backend/app/core/strategy_engine/nodes/edge_and_risk_check.py`

**Modificación**:
- Extender el evaluador de condiciones para acceder a `context.signals`
- Manejar valores `None` en señales (considerar como condición no cumplida)

**Ejemplo**:
```python
def _evaluate_condition(self, condition: Dict[str, Any], context: GraphExecutionContext) -> bool:
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")
    
    # Si el campo es signals.*, acceder a context.signals
    if field.startswith("signals."):
        signal_name = field.replace("signals.", "")
        signal_value = getattr(context, "signals", {}).get(signal_name)
        
        # Si signal_value es None, la condición no se cumple
        if signal_value is None:
            return False
        
        # Evaluar condición con signal_value
        return self._compare_values(signal_value, operator, value)
    
    # ... resto de lógica existente
```

---

## Fase 5: Implementación de Indicadores para Arbitrage/Surebet

### 5.1 Completar ArbitrageProvider

**Ubicación**: `backend/app/core/strategy_engine/indicators/arbitrage_provider.py`

### 5.2 Indicadores a Implementar

#### 5.2.1 `net_arb_gap`
**Descripción**: Diferencia neta de precio entre plataformas después de fees.  
**Fórmula**: `(price_external - price_polymarket - total_fees) / price_polymarket`  
**Rango**: [-∞, ∞] donde > 0.02 (2%) = oportunidad viable  
**Fuente de datos**: 
- `market_state.last_price` (Polymarket)
- `external_data.pinnacle_price` o `external_data.bet365_price`

#### 5.2.2 `latency_delta`
**Descripción**: Diferencia de latencia entre obtener precio de Polymarket vs fuente externa.  
**Fórmula**: `latency_external - latency_polymarket` (en milisegundos)  
**Rango**: [0, ∞] donde < 500ms = aceptable, > 2000ms = unreliable  
**Fuente de datos**: Timestamps de `market_state.last_update` vs `external_data.last_update`

#### 5.2.3 `liquidity_match`
**Descripción**: Proporción de liquidez disponible en ambas plataformas para el tamaño de orden.  
**Fórmula**: `min(liquidity_polymarket, liquidity_external) / order_size`  
**Rango**: [0, 1] donde > 0.8 = suficiente liquidez  
**Fuente de datos**: `market_state.liquidity` y `external_data.liquidity`

#### 5.2.4 `hedge_slippage`
**Descripción**: Slippage estimado al hacer hedge en la segunda plataforma.  
**Fórmula**: `(hedge_execution_price - hedge_mid_price) / hedge_mid_price`  
**Rango**: [-∞, ∞]  
**Fuente de datos**: `external_data.orderbook` para calcular precio de ejecución

#### 5.2.5 `sync_status`
**Descripción**: Estado de sincronización entre plataformas (0 = desincronizado, 1 = sincronizado).  
**Fórmula**: Basado en correlación de precios recientes  
**Rango**: [0, 1]  
**Fuente de datos**: Historial de precios de ambas plataformas

#### 5.2.6 `price_correlation`
**Descripción**: Correlación de precios entre plataformas en ventana temporal.  
**Fórmula**: Coeficiente de correlación de Pearson  
**Rango**: [-1, 1] donde > 0.9 = alta correlación  
**Fuente de datos**: Historial de precios de ambas plataformas

#### 5.2.7 `fill_probability`
**Descripción**: Probabilidad estimada de que ambas órdenes se ejecuten.  
**Fórmula**: `min(fill_prob_polymarket, fill_prob_external)`  
**Rango**: [0, 1]  
**Fuente de datos**: Historial de ejecuciones y liquidez actual

#### 5.2.8 `rejection_risk`
**Descripción**: Riesgo de que una orden sea rechazada (por límites, KYC, etc.).  
**Fórmula**: Basado en historial de rechazos y políticas de la plataforma  
**Rango**: [0, 1] donde 0 = sin riesgo, 1 = alto riesgo  
**Fuente de datos**: `external_data.rejection_history` o configuración

#### 5.2.9 `gas_impact`
**Descripción**: Impacto de costos de gas en la rentabilidad (solo para blockchain).  
**Fórmula**: `gas_cost / order_size`  
**Rango**: [0, ∞] donde valores altos = impacto negativo  
**Fuente de datos**: `external_data.gas_price` y `market_state.gas_estimate`

#### 5.2.10 `arb_persistence`
**Descripción**: Persistencia de la oportunidad de arbitraje (cuánto tiempo ha existido).  
**Fórmula**: `time_opportunity_exists / max_expected_duration`  
**Rango**: [0, 1] donde > 0.5 = oportunidad persistente  
**Fuente de datos**: Timestamp de primera detección vs tiempo actual

### 5.3 Tratamiento de Datos Externos

**Regla de Seguridad**: Si la API externa falla o `latency_delta > 2000ms`, forzar estado `unreliable`.

**Implementación**:
```python
def _check_reliability(self) -> bool:
    """Verifica si los datos son confiables."""
    if not self.external_data:
        return False
    
    latency_delta = self._calculate_latency_delta()
    if latency_delta is None or latency_delta > 2000:
        return False
    
    # Verificar que la API externa respondió recientemente
    last_update = self.external_data.get("last_update")
    if last_update:
        time_since_update = (datetime.utcnow() - last_update).total_seconds()
        if time_since_update > 30:  # Más de 30 segundos = unreliable
            return False
    
    return True

def calculate_all(self) -> Dict[str, Optional[float]]:
    """Calcula indicadores con verificación de confiabilidad."""
    if not self.validate_data():
        return self._empty_signals()
    
    if not self._check_reliability():
        # Forzar estado unreliable: todos los indicadores críticos en None
        signals = self._empty_signals()
        signals["unreliable"] = 1.0  # Flag especial
        return signals
    
    # Calcular indicadores normalmente
    return {
        "net_arb_gap": self._calculate_net_arb_gap(),
        # ... resto
    }
```

### 5.4 Actualizar Factory

**Verificar**: La factory ya debe estar configurada para `surebet_arbitrage` → `ArbitrageProvider`.

---

## Fase 6: Integración Frontend - SignalsMonitor

### 6.1 Crear Componente SignalsMonitor

**Ubicación**: `frontend/components/strategy/SignalsMonitor.tsx`

**Responsabilidades**:
- Renderizar rejilla de tarjetas para cada indicador
- Visualizadores dinámicos según tipo de indicador
- Escuchar WebSocket para actualizaciones en tiempo real
- Cambiar layout según `strategy_type`
- Modo alerta cuando indicadores críticos están en zona roja

### 6.2 Estructura del Componente

```typescript
'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Signal } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUser, useStackApp } from '@stackframe/stack';
import { createTokenGetter } from '@/lib/api';

interface SignalValue {
  value: number | null;
  timestamp: string;
}

interface Signals {
  // Liquidity indicators
  book_imbalance?: SignalValue;
  toxic_flow?: SignalValue;
  inventory_skew?: SignalValue;
  price_drift?: SignalValue;
  spread_elasticity?: SignalValue;
  cancel_rate?: SignalValue;
  rel_liquidity?: SignalValue;
  tw_volatility?: SignalValue;
  res_gap?: SignalValue;
  slippage_impact?: SignalValue;
  
  // Arbitrage indicators
  net_arb_gap?: SignalValue;
  latency_delta?: SignalValue;
  liquidity_match?: SignalValue;
  hedge_slippage?: SignalValue;
  sync_status?: SignalValue;
  price_correlation?: SignalValue;
  fill_probability?: SignalValue;
  rejection_risk?: SignalValue;
  gas_impact?: SignalValue;
  arb_persistence?: SignalValue;
}

interface SignalsMonitorProps {
  strategyId: string;
  strategyType: 'liquidity' | 'surebet_arbitrage';
}

export function SignalsMonitor({ strategyId, strategyType }: SignalsMonitorProps) {
  const [signals, setSignals] = useState<Signals>({});
  const [alertMode, setAlertMode] = useState(false);
  const user = useUser();
  const stackApp = useStackApp();
  
  const token = user ? (createTokenGetter(user, stackApp)() || null) : null;
  const { isConnected, subscribe } = useWebSocket({
    token,
    enabled: !!user && !!strategyId,
  });
  
  // Suscribirse a actualizaciones de DecisionTrace
  useEffect(() => {
    if (!isConnected || !strategyId) return;
    
    const unsubscribe = subscribe('decision_trace', (event: WebSocketEvent) => {
      if (event.payload.strategy_id === strategyId && event.payload.signals) {
        // Convertir signals a formato con timestamp
        const signalsWithTimestamp: Signals = {};
        Object.entries(event.payload.signals).forEach(([key, value]) => {
          signalsWithTimestamp[key] = {
            value: value as number | null,
            timestamp: event.payload.timestamp || new Date().toISOString(),
          };
        });
        setSignals(signalsWithTimestamp);
        
        // Verificar modo alerta
        checkAlertMode(signalsWithTimestamp);
      }
    });
    
    return unsubscribe;
  }, [isConnected, strategyId, subscribe]);
  
  const checkAlertMode = (currentSignals: Signals) => {
    // Indicadores críticos en zona roja
    const criticalRed = 
      (currentSignals.toxic_flow?.value !== null && currentSignals.toxic_flow.value > 0.7) ||
      (currentSignals.rejection_risk?.value !== null && currentSignals.rejection_risk.value > 0.5) ||
      (currentSignals.latency_delta?.value !== null && currentSignals.latency_delta.value > 2000);
    
    setAlertMode(criticalRed);
  };
  
  // Determinar indicadores prioritarios según strategy_type
  const priorityIndicators = strategyType === 'liquidity' 
    ? ['book_imbalance', 'toxic_flow', 'inventory_skew', 'price_drift']
    : ['net_arb_gap', 'latency_delta', 'liquidity_match', 'fill_probability'];
  
  return (
    <div className={`signals-monitor ${alertMode ? 'alert-mode' : ''}`}>
      {/* Renderizar indicadores prioritarios primero */}
      {/* Renderizar resto de indicadores */}
    </div>
  );
}
```

### 6.3 Visualizadores Dinámicos

#### 6.3.1 Barra de Progreso para `book_imbalance`

```typescript
function BookImbalanceIndicator({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted">N/A</span>;
  
  // Normalizar a [0, 100] para la barra
  const normalized = ((value + 1) / 2) * 100; // [-1, 1] -> [0, 100]
  
  // Color reactivo: verde en centro (0.5), rojo en extremos
  const color = 
    normalized < 40 || normalized > 60 ? 'bg-red-500' :
    normalized < 45 || normalized > 55 ? 'bg-yellow-500' :
    'bg-green-500';
  
  return (
    <div>
      <Progress value={normalized} className={color} />
      <span className="text-sm">{value.toFixed(3)}</span>
    </div>
  );
}
```

#### 6.3.2 Indicador de Latencia para `latency_delta`

```typescript
function LatencyIndicator({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted">N/A</span>;
  
  // Estilo señal móvil: verde < 500ms, amarillo < 1000ms, rojo >= 1000ms
  const status = 
    value < 500 ? 'excellent' :
    value < 1000 ? 'good' :
    value < 2000 ? 'warning' :
    'critical';
  
  const colors = {
    excellent: 'bg-green-500',
    good: 'bg-yellow-500',
    warning: 'bg-orange-500',
    critical: 'bg-red-500 animate-pulse',
  };
  
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${colors[status]}`} />
      <span>{value.toFixed(0)}ms</span>
    </div>
  );
}
```

#### 6.3.3 Badge Dinámico para `net_arb_gap`

```typescript
function NetArbGapBadge({ value }: { value: number | null }) {
  if (value === null) return <Badge variant="outline">N/A</Badge>;
  
  const percentage = (value * 100).toFixed(2);
  
  // Rojo < 0%, Verde > 1.5%, Dorado > 3%
  const variant = 
    value < 0 ? 'destructive' :
    value > 0.03 ? 'default' : // Dorado (default con estilo dorado)
    value > 0.015 ? 'default' : // Verde
    'secondary';
  
  const colorClass = 
    value > 0.03 ? 'bg-yellow-500 text-yellow-900' :
    value > 0.015 ? 'bg-green-500 text-green-900' :
    value < 0 ? 'bg-red-500 text-red-900' :
    'bg-gray-500 text-gray-900';
  
  return (
    <Badge className={colorClass}>
      {value > 0 ? '+' : ''}{percentage}%
    </Badge>
  );
}
```

### 6.4 Conexión WebSocket

**Integración**:
- Usar hook `useWebSocket` existente
- Suscribirse al canal `decision_trace`
- Filtrar por `strategy_id`
- Actualizar estado cuando llegue `payload.signals`

**Formato esperado del mensaje WebSocket**:
```json
{
  "type": "decision_trace",
  "payload": {
    "strategy_id": "uuid",
    "timestamp": "2024-05-20T15:30:00Z",
    "signals": {
      "book_imbalance": 0.52,
      "toxic_flow": 0.15,
      "inventory_skew": 0.3
    },
    "decision": "EXECUTE_BUY",
    "reason": "Signals indicate favorable conditions"
  }
}
```

### 6.5 Filtro de Estrategia

**Layout Condicional**:
- Si `strategy_type === "liquidity"`: Priorizar `book_imbalance`, `toxic_flow`, `inventory_skew`
- Si `strategy_type === "surebet_arbitrage"`: Priorizar `net_arb_gap`, `latency_delta`, `liquidity_match`

**Implementación**:
```typescript
const getIndicatorLayout = () => {
  if (strategyType === 'liquidity') {
    return {
      primary: ['book_imbalance', 'toxic_flow'],
      secondary: ['inventory_skew', 'price_drift', 'spread_elasticity'],
      tertiary: ['cancel_rate', 'rel_liquidity', 'tw_volatility', 'res_gap', 'slippage_impact'],
    };
  } else {
    return {
      primary: ['net_arb_gap', 'latency_delta'],
      secondary: ['liquidity_match', 'fill_probability', 'sync_status'],
      tertiary: ['hedge_slippage', 'price_correlation', 'rejection_risk', 'gas_impact', 'arb_persistence'],
    };
  }
};
```

### 6.6 Modo Alerta

**Implementación**:
- Detectar cuando `toxic_flow > 0.7` o `rejection_risk > 0.5` o `latency_delta > 2000`
- Aplicar clase CSS `alert-mode` al contenedor
- Borde parpadeante en rojo usando animación CSS

**CSS**:
```css
.signals-monitor.alert-mode {
  border: 2px solid #ef4444;
  animation: pulse-red 1s infinite;
}

@keyframes pulse-red {
  0%, 100% { border-color: #ef4444; }
  50% { border-color: #dc2626; }
}
```

### 6.7 Integrar en Página Live

**Ubicación**: `frontend/app/strategies/[id]/live/page.tsx`

**Modificación**:
- Importar `SignalsMonitor`
- Agregar sección en el layout
- Pasar `strategyId` y `strategyType` como props

---

## Fase 7: Trazabilidad y Seguridad

### 7.1 Guardar Señales en DecisionTrace

**Ubicación**: `backend/app/core/strategy_engine/nodes/calculate_indicators.py`

**Modificación**:
- Después de calcular señales, guardar en `DecisionTrace` usando `DecisionTraceService`
- Incluir señales en `output_data` del trace

**Implementación**:
```python
from app.core.decision_trace.decision_trace_service import DecisionTraceService

class CalculateIndicatorsNode(GraphNode):
    async def execute(self) -> SuccessResult:
        # ... cálculo de señales ...
        
        # Guardar en DecisionTrace
        trace_service = DecisionTraceService()
        trace_id = getattr(self.context, "trace_id", None)
        if trace_id:
            trace_service.log_decision(
                trace_id=trace_id,
                component="strategy",
                decision_stage="SIGNALS_CALCULATION",
                decision_type="calculation",
                decision="COMPLETED",
                input_data={
                    "strategy_type": strategy_type,
                    "market_state_available": self.market_state is not None,
                    "event_state_available": self.event_state is not None,
                },
                output_data={
                    "signals": signals,
                    "signals_count": len([v for v in signals.values() if v is not None]),
                },
                reason=f"Calculated {len(signals)} indicators for {strategy_type} strategy",
                event_id=self.context.event_id,
            )
        
        return SuccessResult()
```

### 7.2 Manejo de Valores Null en Evaluador de Condiciones

**Ubicación**: `backend/app/core/strategy_engine/nodes/edge_and_risk_check.py`

**Modificación**:
- Si `signal_value is None`, considerar la condición como `False`
- Loggear advertencia si se intenta evaluar señal con valor `None`

**Implementación**:
```python
def _evaluate_condition(self, condition: Dict[str, Any], context: GraphExecutionContext) -> bool:
    field = condition.get("field")
    
    if field.startswith("signals."):
        signal_name = field.replace("signals.", "")
        signal_value = getattr(context, "signals", {}).get(signal_name)
        
        if signal_value is None:
            logger.warning(
                f"Signal {signal_name} is None, condition will evaluate to False",
                extra={"field": field, "condition": condition}
            )
            return False
        
        # Evaluar normalmente
        operator = condition.get("operator")
        value = condition.get("value")
        return self._compare_values(signal_value, operator, value)
    
    # ... resto de lógica
```

### 7.3 Validación de Datos en Proveedores

**Regla**: Cada proveedor debe validar que los datos necesarios estén disponibles antes de calcular.

**Implementación en LiquidityProvider**:
```python
def _calculate_book_imbalance(self) -> Optional[float]:
    """Calcula book_imbalance."""
    if not self.market_state:
        return None
    
    orderbook = self.market_state.get("orderbook")
    if not orderbook:
        return None
    
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])
    
    if not bids or not asks:
        return None
    
    total_bid_volume = sum(bid.get("size", 0) for bid in bids)
    total_ask_volume = sum(ask.get("size", 0) for ask in asks)
    
    if total_bid_volume + total_ask_volume == 0:
        return None
    
    return (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
```

---

## Fase 8: Terminal de Control de Elite

### 8.1 Visión General

**Objetivo**: Crear una terminal de control profesional tipo Bloomberg que permita monitorear y controlar el bot en tiempo real con visibilidad completa del estado del sistema, señales, riesgo y decisiones.

**Filosofía**: No es solo un dashboard, es un "mapa de la pelea" donde ves exactamente qué está haciendo el bot en cada milisegundo.

**📋 Template de Referencia**: El diseño visual y la estructura del layout están definidos en `docs/PENDING/template_estrategy_live_control.html`. Este template HTML muestra:
- Layout de grid con sidebar de eventos, panel central de gráfico/depth, panel de señales, posición y traces
- Estilo visual tipo terminal (fondo oscuro, glassmorphism, tipografía monoespaciada)
- Componentes específicos como Confidence Score, Book Imbalance, Toxic Flow, etc.
- Barra superior con Kill Switch y estadísticas globales
- Footer con shortcuts de teclado y estado del sistema

**Nota**: El template HTML es una referencia visual. La implementación en React/Next.js debe seguir la misma estructura y estilo, pero adaptada a componentes React reutilizables.

### 8.2 Arquitectura del Layout

**Estructura**: Grid de 12 columnas x 6 filas usando CSS Grid o `react-resizable-panels` para paneles redimensionables.

**Ubicación**: `frontend/app/strategies/[id]/live/elite/page.tsx`

**Componente Principal**:
```typescript
'use client';

import { useState, useEffect } from 'react';
import { GlobalStatusBar } from '@/components/strategy/elite/GlobalStatusBar';
import { InteractiveChart } from '@/components/strategy/elite/InteractiveChart';
import { SignalsMonitor } from '@/components/strategy/SignalsMonitor';
import { RiskPositionPanel } from '@/components/strategy/elite/RiskPositionPanel';
import { DecisionTraceList } from '@/components/strategy/elite/DecisionTraceList';

export default function EliteControlPage({ strategyId }: { strategyId: string }) {
  return (
    <div className="grid grid-cols-12 grid-rows-6 h-screen gap-2 bg-black p-2">
      {/* TOP BAR: Panic Button & Status */}
      <header className="col-span-12 row-span-1 border-b border-red-900 bg-slate-950">
        <GlobalStatusBar strategyId={strategyId} />
      </header>

      {/* LEFT: Main Chart & Depth */}
      <main className="col-span-8 row-span-3 border border-slate-800">
        <InteractiveChart strategyId={strategyId} />
      </main>

      {/* RIGHT: Signals Monitor (Expandido) */}
      <aside className="col-span-4 row-span-5 border border-slate-800 bg-slate-900/50">
        <SignalsMonitor strategyId={strategyId} expanded={true} />
      </aside>

      {/* BOTTOM LEFT: Position & Risk */}
      <section className="col-span-4 row-span-2 border border-slate-800">
        <RiskPositionPanel strategyId={strategyId} />
      </section>

      {/* BOTTOM RIGHT: Decision Trace Logs */}
      <section className="col-span-4 row-span-2 border border-slate-800 bg-black">
        <DecisionTraceList strategyId={strategyId} />
      </section>
    </div>
  );
}
```

### 8.3 Panel de Ejecución Central (Main Stage)

**Ubicación**: `frontend/components/strategy/elite/InteractiveChart.tsx`

**Responsabilidades**:
- Gráfico de velas con marcas de órdenes
- Depth Map (Mapa de Calor del Orderbook)
- Live Order Intent Tracker

#### 8.3.1 Gráfico de Precio + Órdenes

**Librería**: `recharts` o `lightweight-charts` (TradingView)

**Características**:
- Gráfico de velas (candlestick) en tiempo real
- Marcas visuales de:
  - **Entradas**: Flechas verdes hacia arriba
  - **Salidas**: Flechas rojas hacia abajo
  - **Órdenes limitadas activas**: Líneas horizontales con etiquetas
- Zoom y pan interactivo
- Indicador de precio actual con línea horizontal

**Estructura**:
```typescript
interface OrderMarker {
  timestamp: string;
  price: number;
  side: 'BUY' | 'SELL';
  type: 'ENTRY' | 'EXIT' | 'LIMIT';
  size: number;
  status: 'FILLED' | 'PENDING' | 'CANCELLED';
}

export function InteractiveChart({ strategyId }: { strategyId: string }) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [orders, setOrders] = useState<OrderMarker[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  // Suscribirse a actualizaciones de precio y órdenes
  useEffect(() => {
    // WebSocket subscription para candles y orders
  }, [strategyId]);

  return (
    <div className="h-full relative">
      <CandlestickChart
        data={candles}
        orders={orders}
        currentPrice={currentPrice}
      />
      <OrderMarkers orders={orders} />
    </div>
  );
}
```

#### 8.3.2 Depth Map (Mapa de Calor del Orderbook)

**Ubicación**: `frontend/components/strategy/elite/DepthMap.tsx`

**Características**:
- Visualización del orderbook en tiempo real
- Mapa de calor que muestra "muros" de liquidez
- Colores:
  - **Verde intenso**: Grandes muros de compra (bids)
  - **Rojo intenso**: Grandes muros de venta (asks)
  - **Amarillo**: Zonas de alta actividad
- Líneas verticales que muestran niveles de precio con mayor liquidez

**Implementación**:
```typescript
export function DepthMap({ orderbook }: { orderbook: Orderbook }) {
  const bids = orderbook.bids || [];
  const asks = orderbook.asks || [];

  // Calcular intensidad de calor por nivel de precio
  const heatMap = useMemo(() => {
    // Agrupar por niveles de precio y sumar volumen
    // Retornar array de { price, volume, intensity }
  }, [bids, asks]);

  return (
    <div className="h-full relative">
      <svg className="w-full h-full">
        {/* Renderizar mapa de calor */}
        {heatMap.map((level, idx) => (
          <rect
            key={idx}
            x={0}
            y={calculateYPosition(level.price)}
            width={calculateWidth(level.intensity)}
            fill={calculateColor(level.intensity)}
            opacity={0.6}
          />
        ))}
      </svg>
    </div>
  );
}
```

#### 8.3.3 Live Order Intent Tracker

**Ubicación**: `frontend/components/strategy/elite/LiveOrderIntentTracker.tsx`

**Características**:
- Tabla pequeña que muestra el estado actual del bot
- Actualización en tiempo real vía WebSocket
- Estados posibles:
  - "Calculando tamaño..."
  - "Esperando confirmación de oráculo..."
  - "Evaluando señales..."
  - "Construyendo plan..."
  - "Esperando aprobación de riesgo..."
  - "Listo para ejecutar"

**Implementación**:
```typescript
interface IntentState {
  stage: string;
  message: string;
  timestamp: string;
  progress?: number; // 0-100
}

export function LiveOrderIntentTracker({ strategyId }: { strategyId: string }) {
  const [intent, setIntent] = useState<IntentState | null>(null);

  useEffect(() => {
    // Suscribirse a actualizaciones de intent desde WebSocket
    const unsubscribe = subscribe('order_intent', (event) => {
      if (event.payload.strategy_id === strategyId) {
        setIntent({
          stage: event.payload.stage,
          message: event.payload.message,
          timestamp: event.payload.timestamp,
          progress: event.payload.progress,
        });
      }
    });

    return unsubscribe;
  }, [strategyId]);

  if (!intent) return null;

  return (
    <div className="absolute bottom-4 left-4 bg-slate-900/90 border border-slate-700 rounded p-2 text-xs">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span className="text-slate-300">{intent.message}</span>
        {intent.progress && (
          <div className="ml-2 w-24 h-1 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all"
              style={{ width: `${intent.progress}%` }}
            />
          </div>
        )}
      </div>
      <div className="text-slate-500 text-xs mt-1">
        {new Date(intent.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}
```

### 8.4 Cuadrante de Signals & Alphas (Derecha)

**Ubicación**: Expandir `frontend/components/strategy/SignalsMonitor.tsx`

**Mejoras sobre SignalsMonitor básico**:
- Visualizaciones más avanzadas (relojes analógicos, barras dinámicas)
- Score de Confianza agregado
- Delta de Oráculo para Surebets

#### 8.4.1 Indicadores de Salud Mejorados

**Visualizaciones**:
- **Relojes Analógicos**: Para indicadores circulares (ej. `book_imbalance` como reloj)
- **Barras Dinámicas**: Con animaciones suaves
- **Gauges**: Para indicadores con rangos (ej. `toxic_flow` como gauge 0-100%)

**Implementación**:
```typescript
function AnalogClockIndicator({ 
  value, 
  label 
}: { 
  value: number | null; 
  label: string;
}) {
  if (value === null) return <span>N/A</span>;

  // Convertir valor a ángulo (ej. book_imbalance [-1, 1] -> [0, 360°])
  const angle = ((value + 1) / 2) * 360;

  return (
    <div className="relative w-24 h-24">
      <svg viewBox="0 0 100 100" className="w-full h-full">
        {/* Círculo de fondo */}
        <circle cx="50" cy="50" r="45" fill="none" stroke="#1e293b" strokeWidth="2" />
        {/* Aguja */}
        <line
          x1="50"
          y1="50"
          x2={50 + 40 * Math.cos((angle - 90) * Math.PI / 180)}
          y2={50 + 40 * Math.sin((angle - 90) * Math.PI / 180)}
          stroke="#10b981"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs text-slate-400">{label}</span>
      </div>
    </div>
  );
}
```

#### 8.4.2 Score de Confianza

**Descripción**: Número del 0 al 100 que resume todos los indicadores.

**Cálculo**:
- Si `strategy_type === "liquidity"`:
  - `toxic_flow < 0.25`: +20 puntos
  - `book_imbalance` entre [0.4, 0.6]: +20 puntos
  - `inventory_skew < 0.7`: +20 puntos
  - `price_drift` estable: +20 puntos
  - Datos frescos: +20 puntos
- Si `strategy_type === "surebet_arbitrage"`:
  - `net_arb_gap > 0.02`: +25 puntos
  - `latency_delta < 500ms`: +25 puntos
  - `liquidity_match > 0.8`: +25 puntos
  - `fill_probability > 0.8`: +25 puntos

**Modo "Cautela"**: Si score < 70, el bot entra en modo cautela (reducción de tamaño de órdenes, validaciones adicionales).

**Implementación**:
```typescript
function ConfidenceScore({ signals, strategyType }: { 
  signals: Signals; 
  strategyType: string;
}) {
  const score = useMemo(() => {
    let total = 0;

    if (strategyType === 'liquidity') {
      if (signals.toxic_flow?.value !== null && signals.toxic_flow.value < 0.25) total += 20;
      if (signals.book_imbalance?.value !== null && 
          signals.book_imbalance.value >= 0.4 && 
          signals.book_imbalance.value <= 0.6) total += 20;
      if (signals.inventory_skew?.value !== null && signals.inventory_skew.value < 0.7) total += 20;
      if (signals.price_drift?.value !== null && Math.abs(signals.price_drift.value) < 0.05) total += 20;
      // Datos frescos (asumir +20 si todas las señales tienen valores)
      const allSignalsPresent = Object.values(signals).every(s => s?.value !== null);
      if (allSignalsPresent) total += 20;
    } else {
      // Arbitrage scoring
      if (signals.net_arb_gap?.value !== null && signals.net_arb_gap.value > 0.02) total += 25;
      if (signals.latency_delta?.value !== null && signals.latency_delta.value < 500) total += 25;
      if (signals.liquidity_match?.value !== null && signals.liquidity_match.value > 0.8) total += 25;
      if (signals.fill_probability?.value !== null && signals.fill_probability.value > 0.8) total += 25;
    }

    return Math.min(100, total);
  }, [signals, strategyType]);

  const status = score >= 70 ? 'confident' : score >= 50 ? 'caution' : 'danger';

  return (
    <div className="p-4 border border-slate-700 rounded">
      <div className="text-sm text-slate-400 mb-2">Confidence Score</div>
      <div className="text-4xl font-bold mb-2" style={{
        color: status === 'confident' ? '#10b981' : 
               status === 'caution' ? '#f59e0b' : '#ef4444'
      }}>
        {score}
      </div>
      {score < 70 && (
        <div className="text-xs text-yellow-500">
          ⚠️ Mode: CAUTION - Reduced order sizes active
        </div>
      )}
    </div>
  );
}
```

#### 8.4.3 Delta de Oráculo (Para Surebets)

**Descripción**: Comparativa de precios en tiempo real entre Polymarket y fuente externa.

**Visualización**: Gráfica de líneas superpuestas con dos series:
- Línea azul: Precio Polymarket
- Línea naranja: Precio fuente externa (Pinnacle/Bet365)
- Área sombreada: Diferencia (gap) entre ambos

**Implementación**:
```typescript
export function OracleDeltaChart({ 
  polymarketPrices, 
  externalPrices 
}: { 
  polymarketPrices: PricePoint[];
  externalPrices: PricePoint[];
}) {
  return (
    <div className="h-48">
      <LineChart width={400} height={200} data={combinedData}>
        <Line 
          type="monotone" 
          dataKey="polymarket" 
          stroke="#3b82f6" 
          strokeWidth={2}
        />
        <Line 
          type="monotone" 
          dataKey="external" 
          stroke="#f97316" 
          strokeWidth={2}
        />
        <Area
          dataKey="gap"
          stroke="none"
          fill="#f97316"
          fillOpacity={0.2}
        />
      </LineChart>
    </div>
  );
}
```

### 8.5 Panel de Inventario y Riesgo (Abajo Izquierda)

**Ubicación**: `frontend/components/strategy/elite/RiskPositionPanel.tsx`

**Componentes**:
1. Posición Actual
2. Inventory Skew Visual
3. Exposure vs Limit

#### 8.5.1 Posición Actual

**Información mostrada**:
- Tamaño neto (posición total)
- Precio promedio de entrada
- PnL no realizado (en verde/rojo)
- PnL realizado (histórico)

**Implementación**:
```typescript
interface Position {
  netSize: number;
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  realizedPnL: number;
}

export function PositionDisplay({ position }: { position: Position }) {
  const pnlColor = position.unrealizedPnL >= 0 ? 'text-green-500' : 'text-red-500';

  return (
    <div className="p-4 space-y-4">
      <div>
        <div className="text-sm text-slate-400">Net Position</div>
        <div className="text-2xl font-bold">
          {position.netSize > 0 ? '+' : ''}{position.netSize.toFixed(4)}
        </div>
      </div>
      
      <div>
        <div className="text-sm text-slate-400">Avg Entry Price</div>
        <div className="text-xl">${position.avgEntryPrice.toFixed(4)}</div>
      </div>

      <div>
        <div className="text-sm text-slate-400">Unrealized P&L</div>
        <div className={`text-2xl font-bold ${pnlColor}`}>
          {position.unrealizedPnL >= 0 ? '+' : ''}${position.unrealizedPnL.toFixed(2)}
        </div>
      </div>

      <div>
        <div className="text-sm text-slate-400">Realized P&L</div>
        <div className={`text-xl ${position.realizedPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
          ${position.realizedPnL.toFixed(2)}
        </div>
      </div>
    </div>
  );
}
```

#### 8.5.2 Inventory Skew Visual

**Descripción**: Balanza visual que muestra exposición total.

**Visualización**: 
- Balanza con dos platos
- Plato izquierdo: Posición objetivo
- Plato derecho: Posición actual (incluyendo pendientes)
- Inclinación de la balanza indica el skew

**Implementación**:
```typescript
export function InventorySkewVisual({ 
  currentPosition, 
  targetPosition, 
  maxPosition 
}: { 
  currentPosition: number;
  targetPosition: number;
  maxPosition: number;
}) {
  const skew = Math.abs(currentPosition - targetPosition) / maxPosition;
  const tilt = ((currentPosition - targetPosition) / maxPosition) * 15; // Grados de inclinación

  return (
    <div className="p-4">
      <div className="text-sm text-slate-400 mb-4">Inventory Skew</div>
      <div className="relative h-32 flex items-center justify-center">
        {/* Balanza */}
        <svg viewBox="0 0 200 100" className="w-full h-full">
          {/* Base */}
          <line x1="100" y1="80" x2="100" y2="50" stroke="#475569" strokeWidth="2" />
          
          {/* Barra de balanza (con inclinación) */}
          <g transform={`rotate(${tilt} 100 50)`}>
            <line x1="20" y1="50" x2="180" y2="50" stroke="#64748b" strokeWidth="3" />
            
            {/* Plato izquierdo (target) */}
            <ellipse cx="30" cy="50" rx="15" ry="5" fill="#1e293b" stroke="#475569" />
            <text x="30" y="45" textAnchor="middle" className="text-xs fill-slate-400">
              Target
            </text>
            
            {/* Plato derecho (current) */}
            <ellipse cx="170" cy="50" rx="15" ry="5" fill="#1e293b" stroke="#475569" />
            <text x="170" y="45" textAnchor="middle" className="text-xs fill-slate-400">
              Current
            </text>
          </g>
        </svg>
      </div>
      <div className="text-center mt-2">
        <span className={`text-lg font-bold ${
          skew < 0.3 ? 'text-green-500' : 
          skew < 0.7 ? 'text-yellow-500' : 
          'text-red-500'
        }`}>
          {skew.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
```

#### 8.5.3 Exposure vs Limit

**Descripción**: Barra de progreso que muestra cuánto del "Max Exposure" está comprometido.

**Implementación**:
```typescript
export function ExposureBar({ 
  currentExposure, 
  maxExposure 
}: { 
  currentExposure: number;
  maxExposure: number;
}) {
  const percentage = (currentExposure / maxExposure) * 100;
  const color = 
    percentage < 50 ? 'bg-green-500' :
    percentage < 80 ? 'bg-yellow-500' :
    'bg-red-500';

  return (
    <div className="p-4">
      <div className="flex justify-between text-sm mb-2">
        <span className="text-slate-400">Exposure</span>
        <span className="text-slate-300">
          ${currentExposure.toFixed(2)} / ${maxExposure.toFixed(2)}
        </span>
      </div>
      <div className="w-full h-4 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${Math.min(100, percentage)}%` }}
        />
      </div>
      {percentage > 80 && (
        <div className="text-xs text-yellow-500 mt-2">
          ⚠️ Approaching exposure limit
        </div>
      )}
    </div>
  );
}
```

### 8.6 Decision Trace & Logs de Auditoría (Abajo Derecha)

**Ubicación**: `frontend/components/strategy/elite/DecisionTraceList.tsx`

**Características**:
- Feed de texto de alta velocidad
- Explica cada paso del Grafo de Decisión
- Filtros de gravedad (Warnings, Errors)
- Búsqueda y filtrado por componente

**Implementación**:
```typescript
interface TraceEntry {
  timestamp: string;
  component: string;
  stage: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  data?: any;
}

export function DecisionTraceList({ strategyId }: { strategyId: string }) {
  const [traces, setTraces] = useState<TraceEntry[]>([]);
  const [filter, setFilter] = useState<'all' | 'warning' | 'error'>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    // Suscribirse a DecisionTrace vía WebSocket
    const unsubscribe = subscribe('decision_trace', (event) => {
      if (event.payload.strategy_id === strategyId) {
        setTraces(prev => [
          {
            timestamp: event.payload.timestamp,
            component: event.payload.component,
            stage: event.payload.decision_stage,
            message: formatTraceMessage(event.payload),
            severity: determineSeverity(event.payload),
            data: event.payload,
          },
          ...prev.slice(0, 999), // Mantener últimos 1000
        ]);
      }
    });

    return unsubscribe;
  }, [strategyId]);

  const formatTraceMessage = (payload: any): string => {
    // Formatear mensaje según el stage
    if (payload.decision_stage === 'SIGNALS_CALCULATION') {
      return `[Signal] ${payload.reason || 'Calculated indicators'}`;
    } else if (payload.decision_stage === 'RISK') {
      return `[Risk] ${payload.reason || 'Risk check completed'}`;
    } else if (payload.decision_stage === 'EXECUTION') {
      return `[Execution] ${payload.reason || 'Execution intent emitted'}`;
    }
    return `[${payload.component}] ${payload.reason || 'Processing'}`;
  };

  const filteredTraces = traces.filter(trace => {
    if (filter !== 'all' && trace.severity !== filter) return false;
    if (search && !trace.message.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="h-full flex flex-col bg-black">
      {/* Header con filtros */}
      <div className="p-2 border-b border-slate-800 flex gap-2">
        <input
          type="text"
          placeholder="Search traces..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm"
        />
        <div className="flex gap-1">
          <button
            onClick={() => setFilter('all')}
            className={`px-2 py-1 text-xs rounded ${
              filter === 'all' ? 'bg-slate-700' : 'bg-slate-800'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('warning')}
            className={`px-2 py-1 text-xs rounded ${
              filter === 'warning' ? 'bg-yellow-900' : 'bg-slate-800'
            }`}
          >
            Warnings
          </button>
          <button
            onClick={() => setFilter('error')}
            className={`px-2 py-1 text-xs rounded ${
              filter === 'error' ? 'bg-red-900' : 'bg-slate-800'
            }`}
          >
            Errors
          </button>
        </div>
      </div>

      {/* Lista de traces */}
      <div className="flex-1 overflow-y-auto font-mono text-xs">
        {filteredTraces.map((trace, idx) => (
          <div
            key={idx}
            className={`p-2 border-b border-slate-900 hover:bg-slate-900 ${
              trace.severity === 'error' ? 'bg-red-950/20' :
              trace.severity === 'warning' ? 'bg-yellow-950/20' :
              ''
            }`}
          >
            <div className="flex items-start gap-2">
              <span className="text-slate-500 text-xs">
                {new Date(trace.timestamp).toLocaleTimeString()}
              </span>
              <span className={`text-xs ${
                trace.severity === 'error' ? 'text-red-400' :
                trace.severity === 'warning' ? 'text-yellow-400' :
                'text-slate-300'
              }`}>
                {trace.message}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 8.7 Barra de "Panic & Override" (Superior)

**Ubicación**: `frontend/components/strategy/elite/GlobalStatusBar.tsx`

**Componentes**:
1. Kill Switch Global
2. Modo de Operación
3. Status de Conectividad

#### 8.7.1 Kill Switch Global

**Descripción**: Botón rojo gigante para detener todas las estrategias y cancelar órdenes abiertas.

**Implementación**:
```typescript
export function KillSwitch({ strategyId }: { strategyId: string }) {
  const [isActive, setIsActive] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const handleKill = async () => {
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000); // Requiere 3 segundos de confirmación
      return;
    }

    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.post(`/strategies/${strategyId}/kill`, {
        cancel_orders: true,
        reason: 'Manual kill switch activated',
      });
      setIsActive(false);
      setConfirming(false);
    } catch (error) {
      console.error('Error activating kill switch:', error);
    }
  };

  return (
    <button
      onClick={handleKill}
      className={`
        px-8 py-4 rounded-lg font-bold text-white transition-all
        ${confirming 
          ? 'bg-red-600 animate-pulse' 
          : 'bg-red-700 hover:bg-red-600'
        }
      `}
    >
      {confirming ? 'CONFIRM KILL' : 'KILL SWITCH'}
    </button>
  );
}
```

#### 8.7.2 Modo de Operación

**Descripción**: Switch para cambiar entre DRY_RUN, PAPER y LIVE.

**Implementación**:
```typescript
export function OperationModeSwitch({ strategyId }: { strategyId: string }) {
  const [mode, setMode] = useState<'DRY_RUN' | 'PAPER' | 'LIVE'>('PAPER');

  const handleModeChange = async (newMode: 'DRY_RUN' | 'PAPER' | 'LIVE') => {
    if (newMode === 'LIVE') {
      // Requerir confirmación adicional
      const confirmed = window.confirm(
        '⚠️ WARNING: Switching to LIVE mode. Real money will be used. Continue?'
      );
      if (!confirmed) return;
    }

    try {
      const api = initApiClient(createTokenGetter(user, stackApp));
      await api.put(`/strategies/${strategyId}/execution-mode`, {
        mode: newMode,
      });
      setMode(newMode);
    } catch (error) {
      console.error('Error changing execution mode:', error);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-400">Mode:</span>
      <div className="flex gap-1 bg-slate-900 rounded p-1">
        {(['DRY_RUN', 'PAPER', 'LIVE'] as const).map((m) => (
          <button
            key={m}
            onClick={() => handleModeChange(m)}
            className={`px-3 py-1 text-xs rounded transition-all ${
              mode === m
                ? m === 'LIVE' 
                  ? 'bg-red-600 text-white' 
                  : 'bg-slate-700 text-white'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            {m}
          </button>
        ))}
      </div>
    </div>
  );
}
```

#### 8.7.3 Status de Conectividad

**Descripción**: Tres puntos de luz que indican estado de conexión.

**Implementación**:
```typescript
interface ConnectivityStatus {
  polymarket: 'connected' | 'disconnected' | 'reconnecting';
  external: 'connected' | 'disconnected' | 'reconnecting';
  backend: 'connected' | 'disconnected' | 'reconnecting';
}

export function ConnectivityStatus({ status }: { status: ConnectivityStatus }) {
  const getStatusColor = (s: string) => {
    if (s === 'connected') return 'bg-green-500';
    if (s === 'reconnecting') return 'bg-yellow-500 animate-pulse';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor(status.polymarket)}`} />
        <span className="text-xs text-slate-400">Polymarket</span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor(status.external)}`} />
        <span className="text-xs text-slate-400">External API</span>
      </div>
      <div className="flex items-center gap-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor(status.backend)}`} />
        <span className="text-xs text-slate-400">Backend</span>
      </div>
    </div>
  );
}
```

### 8.8 Funcionalidades Avanzadas

#### 8.8.1 Replay Mode

**Descripción**: Permite arrastrar el tiempo hacia atrás para ver qué indicadores había exactamente en el momento de un trade pasado.

**Implementación**:
```typescript
export function ReplayMode({ strategyId }: { strategyId: string }) {
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayTime, setReplayTime] = useState<Date | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x, 2x, 5x, 10x

  const handleReplay = async (targetTime: Date) => {
    setIsReplaying(true);
    setReplayTime(targetTime);

    // Cargar datos históricos desde API
    const api = initApiClient(createTokenGetter(user, stackApp));
    const historicalData = await api.get(`/strategies/${strategyId}/history`, {
      params: { timestamp: targetTime.toISOString() },
    });

    // Actualizar todos los componentes con datos históricos
    // ...
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => setIsReplaying(!isReplaying)}
        className="px-3 py-1 text-xs bg-slate-800 rounded"
      >
        {isReplaying ? 'Stop Replay' : 'Replay Mode'}
      </button>
      {isReplaying && (
        <>
          <input
            type="datetime-local"
            value={replayTime ? replayTime.toISOString().slice(0, 16) : ''}
            onChange={(e) => setReplayTime(new Date(e.target.value))}
            className="px-2 py-1 text-xs bg-slate-900 border border-slate-700 rounded"
          />
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
            className="px-2 py-1 text-xs bg-slate-900 border border-slate-700 rounded"
          >
            <option value={1}>1x</option>
            <option value={2}>2x</option>
            <option value={5}>5x</option>
            <option value={10}>10x</option>
          </select>
        </>
      )}
    </div>
  );
}
```

#### 8.8.2 Sonidos de Alerta

**Descripción**: Sonidos sutiles estilo Bloomberg para eventos importantes.

**Eventos con sonido**:
- Arbitraje Gap > 3%: Sonido de "ding" suave
- Toxic Flow entra en rojo: Sonido de advertencia
- Orden ejecutada: Sonido de confirmación
- Kill switch activado: Sonido de alerta crítica

**Implementación**:
```typescript
const useAlertSounds = () => {
  const playSound = (type: 'arbitrage' | 'toxic' | 'execution' | 'kill') => {
    const audio = new Audio();
    
    switch (type) {
      case 'arbitrage':
        // Sonido de "ding" suave
        audio.src = '/sounds/arbitrage-ding.mp3';
        audio.volume = 0.3;
        break;
      case 'toxic':
        // Sonido de advertencia
        audio.src = '/sounds/toxic-warning.mp3';
        audio.volume = 0.5;
        break;
      case 'execution':
        // Sonido de confirmación
        audio.src = '/sounds/execution-confirm.mp3';
        audio.volume = 0.4;
        break;
      case 'kill':
        // Sonido de alerta crítica
        audio.src = '/sounds/kill-alert.mp3';
        audio.volume = 0.7;
        break;
    }
    
    audio.play().catch(console.error);
  };

  return { playSound };
};

// Uso en componente
export function SignalsMonitor({ strategyId }: { strategyId: string }) {
  const { playSound } = useAlertSounds();

  useEffect(() => {
    if (signals.net_arb_gap?.value && signals.net_arb_gap.value > 0.03) {
      playSound('arbitrage');
    }
    if (signals.toxic_flow?.value && signals.toxic_flow.value > 0.7) {
      playSound('toxic');
    }
  }, [signals]);
}
```

#### 8.8.3 Keyboard Shortcuts

**Descripción**: Atajos de teclado para control rápido.

**Shortcuts**:
- `Space`: Pausar/Reanudar bot
- `Arrow Up`: Aumentar agresividad (reducir spread mínimo)
- `Arrow Down`: Reducir agresividad (aumentar spread mínimo)
- `K`: Activar Kill Switch (con confirmación)
- `R`: Activar Replay Mode
- `M`: Cambiar modo de operación (DRY_RUN → PAPER → LIVE)

**Implementación**:
```typescript
export function useKeyboardShortcuts(strategyId: string) {
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ignorar si está escribiendo en un input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          // Toggle pause
          break;
        case 'ArrowUp':
          e.preventDefault();
          // Increase aggressiveness
          break;
        case 'ArrowDown':
          e.preventDefault();
          // Decrease aggressiveness
          break;
        case 'k':
        case 'K':
          e.preventDefault();
          // Activate kill switch
          break;
        case 'r':
        case 'R':
          e.preventDefault();
          // Toggle replay mode
          break;
        case 'm':
        case 'M':
          e.preventDefault();
          // Cycle execution mode
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [strategyId]);
}
```

### 8.9 Integración y Routing

**Ruta**: `/strategies/[id]/live/elite`

**Modificación en página live existente**:
```typescript
// frontend/app/strategies/[id]/live/page.tsx
import Link from 'next/link';

export default function StrategyLivePage({ params }: { params: { id: string } }) {
  return (
    <Layout>
      <div className="mb-4">
        <Link 
          href={`/strategies/${params.id}/live/elite`}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          🚀 Open Elite Control Terminal
        </Link>
      </div>
      {/* ... resto del contenido normal ... */}
    </Layout>
  );
}
```

---

## Fase 9: Testing y Validación

### 9.1 Tests Unitarios

**Ubicación**: `backend/tests/unit/test_indicators/`

**Archivos a crear**:
- `test_base.py` - Tests de clase base
- `test_factory.py` - Tests de factory
- `test_liquidity_provider.py` - Tests de indicadores de liquidez
- `test_arbitrage_provider.py` - Tests de indicadores de arbitraje
- `test_calculate_indicators_node.py` - Tests del nodo

**Casos de prueba**:
- Cálculo correcto de cada indicador
- Manejo de datos faltantes (retornar `None`)
- Validación de datos
- Factory con tipos válidos e inválidos
- Integración con GraphExecutionContext

### 8.2 Tests de Integración

**Ubicación**: `backend/tests/integration/test_strategy_engine/`

**Archivos a crear**:
- `test_signals_in_decision_graph.py` - Tests de flujo completo

**Casos de prueba**:
- Ejecución de Decision Graph con nodo `calculate_indicators`
- Inyección de señales en contexto
- Evaluación de condiciones basadas en señales
- Guardado en DecisionTrace

### 8.3 Tests Frontend

**Ubicación**: `frontend/components/strategy/__tests__/`

**Archivos a crear**:
- `SignalsMonitor.test.tsx` - Tests del componente

**Casos de prueba**:
- Renderizado de indicadores
- Actualización vía WebSocket
- Modo alerta
- Layout condicional según strategy_type

### 9.4 Tests de Alertas de Combate ⚠️ **CRÍTICO**

**Ubicación**: `backend/tests/unit/test_indicators/test_alertas_combate.py`

**Casos de prueba críticos**:

#### 9.4.1 Tests de Stale Data
- [ ] `check_data_freshness()` retorna `False` cuando datos son > max_age_ms
- [ ] `check_data_freshness()` retorna `True` cuando datos son frescos
- [ ] Indicadores retornan `None` cuando datos son obsoletos
- [ ] Logging de advertencias cuando se detecta stale data
- [ ] Manejo de timestamps en diferentes formatos (ISO, Unix, etc.)

#### 9.4.2 Tests de Memoización
- [ ] `memoize()` calcula función solo una vez por tick
- [ ] Cache se limpia correctamente entre ticks
- [ ] Múltiples indicadores comparten cálculos memoizados (ej. price_history)
- [ ] Performance: verificar que memoización reduce tiempo de cálculo

#### 9.4.3 Tests de inventory_skew Sincronización
- [ ] `inventory_skew` incluye órdenes pendientes en cálculo
- [ ] `inventory_skew` retorna `None` si `risk_state` es obsoleto (> 2 segundos)
- [ ] `inventory_skew` maneja correctamente órdenes con diferentes estados (PENDING, SUBMITTED, PARTIALLY_FILLED)
- [ ] Validación de que `risk_state` tiene campo `pending_orders`

### 9.5 Validación Manual

**Checklist**:
- [ ] Indicadores se calculan correctamente con datos reales
- [ ] Señales se inyectan en `context.signals`
- [ ] Condiciones en JSON de estrategia funcionan con señales
- [ ] DecisionTrace contiene señales en `output_data`
- [ ] Frontend muestra indicadores en tiempo real
- [ ] Modo alerta se activa correctamente
- [ ] Layout cambia según `strategy_type`
- [ ] Manejo de `None` no crashea el sistema
- [ ] **⚠️ Stale Data**: Indicadores retornan `None` cuando datos son obsoletos
- [ ] **⚠️ Memoización**: Cálculos pesados se ejecutan una sola vez por tick
- [ ] **⚠️ inventory_skew**: Sincronización correcta con órdenes pendientes

---

## Orden de Implementación Recomendado

### Sprint 1 (Backend Base)
1. Fase 1: Estructura base (base.py, factory.py, liquidity_provider.py estructura)
2. Fase 2: Implementar 3-4 indicadores de liquidez más simples (book_imbalance, price_drift, etc.)
3. Fase 3: Crear nodo CalculateIndicatorsNode y registrar en GraphRuntime

### Sprint 2 (Backend Completo)
4. Fase 2: Completar todos los 10 indicadores de liquidez
5. Fase 4: Actualizar JSON de estrategia y EdgeAndRiskCheckNode
6. Fase 7: Integración con DecisionTrace

### Sprint 3 (Arbitrage)
7. Fase 5: Implementar todos los indicadores de arbitraje
8. Fase 5: Crear JSON de estrategia surebet_strategy.json
9. Testing backend completo

### Sprint 4 (Frontend Básico)
10. Fase 6: Crear componente SignalsMonitor
11. Fase 6: Implementar visualizadores dinámicos
12. Fase 6: Integrar WebSocket y modo alerta
13. Fase 6: Integrar en página live
14. Testing frontend básico

### Sprint 5 (Terminal Elite)
15. Fase 8: Crear layout de Terminal Elite
16. Fase 8: Implementar InteractiveChart con Depth Map
17. Fase 8: Implementar RiskPositionPanel
18. Fase 8: Implementar DecisionTraceList
19. Fase 8: Implementar GlobalStatusBar con Kill Switch
20. Fase 8: Añadir funcionalidades avanzadas (Replay, Sonidos, Shortcuts)
21. Testing terminal elite completo

### Sprint 6 (Quant Engine - Indicadores de Rentabilidad) 🆕
22. Fase 2.3: Implementar `expected_roi_at_depth`
23. Fase 2.3: Implementar `capital_absorption_capacity`
24. Fase 2.3: Implementar `time_value_score`
25. Fase 2.3: Implementar `slippage_impact_100k`
26. Fase 2.3: Integrar indicadores de rentabilidad en `LiquidityProvider`
27. Testing de indicadores de rentabilidad

### Sprint 7 (Watcher con Filtros Avanzados) 🆕
28. Fase 10: Implementar ROI Filter
29. Fase 10: Implementar Time Filter
30. Fase 10: Implementar Safety Filters
31. Fase 10: Implementar lógica de despliegue de capital
32. Fase 10: Integrar filtros en Watcher Engine
33. Testing de filtros de watcher

### Sprint 8 (Terminal Elite V3.1) 🆕
34. Fase 11: Implementar Profit Depth Chart
35. Fase 11: Implementar Trade Book Visualizer
36. Fase 11: Implementar ROI Event Selector
37. Fase 11: Implementar Selection Audit Log
38. Fase 11: Actualizar layout según template V3.1
39. Testing terminal V3.1 completo

### Sprint 9 (Sincronización en Tiempo Real) 🆕
40. Fase 12: Implementar Real-Time Depth Sync (WebSocket L2)
41. Fase 12: Implementar Pending Balance Management
42. Fase 12: Implementar Hedge Matcher para arbitraje
43. Fase 12: Integrar sincronización en tiempo real
44. Testing de sincronización completo

---

## ⚠️ Alertas de Combate (Sugerencias Tácticas)

Esta sección documenta las alertas críticas identificadas durante el diseño y que deben implementarse para evitar errores costosos en producción.

### 1. Stale Data Protection ⚠️ **CRÍTICO**

**Problema**: Un indicador puede tener datos, pero si el orderbook es de hace 10 segundos, el `book_imbalance` es peligroso.

**Solución Implementada**:
- Método `check_data_freshness()` en clase base `SignalProvider`
- Validación automática en cada cálculo de indicador
- Retornar `None` si datos son obsoletos (en lugar de calcular con datos incorrectos)
- Logging de advertencias para debugging

**Configuración Recomendada**:
- `market_state.orderbook`: 5000ms (5 segundos)
- `risk_state`: 2000ms (2 segundos) - **CRÍTICO para inventory_skew**
- `external_data`: 30000ms (30 segundos)

**Tests Requeridos**: Ver sección 9.4.1

### 2. Eficiencia con Memoización ⚠️ **IMPORTANTE**

**Problema**: Si tienes 20 indicadores y cada uno hace cálculos pesados (ej. procesar historial de precios), podrías ralentizar el ControlLoop.

**Solución Implementada**:
- Sistema de memoización en clase base `SignalProvider`
- Método `memoize()` para cachear cálculos intermedios
- Ejemplo: `price_drift` y `tw_volatility` comparten historial procesado
- Cache se limpia automáticamente al inicio de cada tick

**Ejemplo de Uso**:
```python
# En lugar de procesar historial dos veces:
price_history = self._process_price_history()  # Para price_drift
price_history = self._process_price_history()  # Para tw_volatility (redundante)

# Usar memoización:
price_history = self._get_price_history_processed()  # Calcula una vez
# Ambos indicadores usan el mismo historial procesado
```

**Tests Requeridos**: Ver sección 9.4.2

### 3. inventory_skew Sincronización ⚠️ **CRÍTICO**

**Problema**: Este indicador es el más delicado porque depende de tu estado interno, no del mercado. Si hay una orden en vuelo (pending), el skew podría ser erróneo.

**Solución Implementada**:
- Ajuste de posición con órdenes pendientes antes de calcular skew
- Validación de freshness del `risk_state` (max 2 segundos)
- Inclusión de órdenes con estados: PENDING, SUBMITTED, PARTIALLY_FILLED
- Retornar `None` si `risk_state` es obsoleto (en lugar de calcular con datos incorrectos)

**Implementación**:
```python
# Ajustar posición efectiva con órdenes pendientes
pending_position_delta = sum(
    order.get("size", 0) * (1 if order.get("side") == "BUY" else -1)
    for order in pending_orders
    if order.get("status") in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]
)
effective_position = current_position + pending_position_delta
```

**Tests Requeridos**: Ver sección 9.4.3

### Checklist de Implementación de Alertas

- [ ] `check_data_freshness()` implementado en `SignalProvider`
- [ ] Todos los indicadores validan freshness antes de calcular
- [ ] Sistema de memoización implementado y funcionando
- [ ] `inventory_skew` incluye órdenes pendientes
- [ ] `inventory_skew` valida freshness de `risk_state` (< 2 segundos)
- [ ] Tests de alertas de combate pasando
- [ ] Logging de advertencias cuando se detectan problemas

---

## Consideraciones Técnicas

### Performance
- Los indicadores deben calcularse rápidamente (< 10ms por indicador)
- **⚠️ Usar memoización** para evitar cálculos redundantes
- Cachear cálculos intermedios cuando sea posible
- Usar operaciones vectorizadas si hay arrays grandes
- **⚠️ Validar freshness** antes de calcular (evitar cálculos con datos obsoletos)

### Seguridad
- Validar todos los inputs antes de calcular
- **⚠️ Validar freshness de datos** (Stale Data Protection)
- No exponer información sensible en señales
- Manejar errores sin exponer stack traces
- **⚠️ Sincronización correcta** con estado de órdenes pendientes

### Mantenibilidad
- Documentar fórmulas de cada indicador
- Incluir ejemplos de uso en docstrings
- Mantener tests actualizados
- **⚠️ Documentar alertas de combate** en código

---

## Fase 10: Watcher con Filtros de Selección Avanzados (Quant Engine)

### 10.1 Visión General

**Objetivo**: Transformar el Watcher de un simple disparador por tiempo a un **Filtro de Oportunidades** que evalúa rentabilidad antes de activar estrategias.

**Filosofía**: No activar estrategias en eventos que no cumplan criterios de rentabilidad mínima. El Watcher debe ser un "gatekeeper" inteligente.

### 10.2 Filtros de Entrada (Gatekeeping)

#### 10.2.1 ROI Filter
**Descripción**: `roi > 0.06` (6%). Si la profundidad del libro no permite este retorno para al menos una cantidad mínima de capital, el evento se ignora.

**Implementación**:
```python
def _check_roi_filter(self, event_id: UUID) -> bool:
    """
    Verifica si el evento cumple el filtro de ROI mínimo.
    
    Returns:
        True si expected_roi_at_depth >= min_roi_threshold
    """
    # Obtener capacidad de absorción con ROI threshold
    min_roi = 0.06  # 6%
    capacity = self._calculate_capital_absorption_capacity(min_roi)
    
    if capacity is None or capacity < 1000:  # Mínimo $1000
        return False
    
    # Verificar que el ROI esperado sea >= threshold
    expected_roi = self._calculate_expected_roi_at_depth(capacity)
    if expected_roi is None or expected_roi < min_roi:
        return False
    
    return True
```

#### 10.2.2 Time Filter
**Descripción**: `time_to_resolution < 10min`. Evita bloqueos de capital prolongados.

**Implementación**:
```python
def _check_time_filter(self, event_id: UUID) -> bool:
    """
    Verifica si el tiempo hasta resolución es aceptable.
    
    Returns:
        True si time_to_resolution < 10 minutos
    """
    if not self.event_state:
        return False
    
    close_time = self.event_state.get("close_time")
    if not close_time:
        return False
    
    if isinstance(close_time, str):
        close_time = datetime.fromisoformat(close_time.replace('Z', '+00:00'))
    
    time_remaining = (close_time - datetime.utcnow()).total_seconds() / 60
    return 0 < time_remaining < 10  # Entre 0 y 10 minutos
```

#### 10.2.3 Safety Filters
**Descripción**: Combinación de `toxic_flow < 0.25` y `spread < 0.001`.

**Implementación**:
```python
def _check_safety_filters(self) -> bool:
    """
    Verifica filtros de seguridad.
    
    Returns:
        True si toxic_flow < 0.25 Y spread < 0.001
    """
    toxic_flow = self._calculate_toxic_flow()
    if toxic_flow is None or toxic_flow >= 0.25:
        return False
    
    spread = self.market_state.get("spread") if self.market_state else None
    if spread is None or spread >= 0.001:
        return False
    
    return True
```

### 10.3 Lógica de Despliegue de Capital

**Problema**: El Watcher debe decidir cuánto capital de los 100k asignar a cada "hilo" de evento basado en la `absorption_capacity`.

**Implementación**:
```python
def _calculate_capital_allocation(
    self, 
    event_id: UUID, 
    available_balance: float
) -> Optional[float]:
    """
    Calcula cuánto capital asignar a este evento.
    
    Args:
        event_id: ID del evento
        available_balance: Balance disponible (descontando órdenes pendientes)
    
    Returns:
        Capital a asignar (en USDC) o None si no cumple filtros
    """
    # Verificar todos los filtros
    if not self._check_roi_filter(event_id):
        logger.info(f"Event {event_id} rejected: ROI filter failed")
        return None
    
    if not self._check_time_filter(event_id):
        logger.info(f"Event {event_id} rejected: Time filter failed")
        return None
    
    if not self._check_safety_filters():
        logger.info(f"Event {event_id} rejected: Safety filters failed")
        return None
    
    # Calcular capacidad de absorción
    capacity = self._calculate_capital_absorption_capacity()
    if capacity is None:
        return None
    
    # Asignar capital (limitado por balance disponible)
    allocated_capital = min(capacity, available_balance)
    
    return allocated_capital if allocated_capital > 0 else None
```

### 10.4 Integración en Watcher Engine

**Ubicación**: `backend/app/core/event_watch_engine/watcher.py`

**Modificación**: El watcher debe llamar a `LiquidityProvider` para calcular indicadores de rentabilidad antes de activar estrategias.

---

## Fase 11: Terminal Elite V3.1 (Visualización de Profundidad)

### 11.1 Actualización de Componentes Frontend

#### 11.1.1 Profit Depth Chart
**Ubicación**: `frontend/components/strategy/elite/ProfitDepthChart.tsx`

**Descripción**: Gráfica central que mapea niveles de precio vs. ROI porcentual.

**Implementación**:
```typescript
interface DepthLevel {
  price: number;
  liquidity: number;
  roi: number;
  capitalRequired: number;
}

export function ProfitDepthChart({ 
  depthLevels, 
  capitalAllocation 
}: { 
  depthLevels: DepthLevel[];
  capitalAllocation: number;
}) {
  return (
    <div className="h-full flex flex-col">
      <h3 className="text-[10px] font-black text-slate-500 uppercase mb-4">
        Análisis de Profundidad por Nivel
      </h3>
      <div className="space-y-3">
        {depthLevels.map((level, idx) => (
          <div key={idx} className="group relative">
            <div className="flex justify-between text-[10px] mb-1 mono">
              <span className="text-slate-400">
                Cuota {level.price.toFixed(2)} 
                <span className="text-slate-600"> (${level.liquidity.toFixed(0)} disp)</span>
              </span>
              <span className={`font-bold ${
                level.roi >= 0.06 ? 'text-green-500' : 'text-slate-500'
              }`}>
                {(level.roi * 100).toFixed(2)}% ROI
              </span>
            </div>
            <div className="depth-bar">
              <div 
                className="depth-fill" 
                style={{ 
                  width: `${(level.capitalRequired / capitalAllocation) * 100}%`,
                  background: level.roi >= 0.06 
                    ? 'rgba(59, 130, 246, 0.2)' 
                    : 'rgba(16, 185, 129, 0.15)',
                  borderColor: level.roi >= 0.06 ? '#3b82f6' : '#10b981'
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### 11.1.2 Trade Book Visualizer
**Ubicación**: `frontend/components/strategy/elite/TradeBookVisualizer.tsx`

**Descripción**: Barras horizontales que muestran la liquidez disponible en cada nivel de retorno.

#### 11.1.3 Selector de Eventos ROI-Focus
**Ubicación**: `frontend/components/strategy/elite/ROIEventSelector.tsx`

**Descripción**: Sidebar que destaca el ROI esperado y la capacidad de cada partido/evento.

**Características**:
- Muestra eventos filtrados por ROI > 6%
- Indica capacidad de absorción de capital
- Muestra tiempo hasta resolución
- Destaca eventos activos vs ignorados

#### 11.1.4 Audit Log de Selección
**Ubicación**: `frontend/components/strategy/elite/SelectionAuditLog.tsx`

**Descripción**: Logs que explican decisiones del watcher:
- "Evento ignorado: ROI 3% < 6% requerido"
- "Desplegando 18k: Capacidad máxima para ROI > 6% alcanzada"
- "Filtro de tiempo: Evento resuelve en 15min > 10min máximo"

---

## Fase 12: Sincronización de Balance y Órdenes

### 12.1 Real-Time Depth Sync

**Descripción**: Suscripción al L2 Orderbook de Polymarket para recalcular el ROI cada vez que cambie un solo contrato en el libro.

**Implementación**:
- Integrar WebSocket de Polymarket L2 Orderbook
- Recalcular `expected_roi_at_depth` y `capital_absorption_capacity` en tiempo real
- Actualizar UI cuando cambien los indicadores de rentabilidad

### 12.2 Pending Balance Management

**Descripción**: El motor de selección debe restar el capital "en vuelo" (órdenes abiertas) del balance de 100k para no intentar comprar más de lo disponible.

**Implementación**:
```python
def _get_available_balance(self) -> float:
    """
    Calcula balance disponible descontando órdenes pendientes.
    
    Returns:
        Balance disponible para nuevas operaciones
    """
    total_balance = self.risk_state.get("total_balance", 100000) if self.risk_state else 100000
    
    # Obtener órdenes pendientes
    pending_orders = self.risk_state.get("pending_orders", []) if self.risk_state else []
    
    # Calcular capital comprometido
    committed_capital = sum(
        float(order.get("size", 0)) * float(order.get("price", 0))
        for order in pending_orders
        if order.get("status") in ["PENDING", "SUBMITTED", "PARTIALLY_FILLED"]
    )
    
    available_balance = total_balance - committed_capital
    return max(0, available_balance)
```

### 12.3 Hedge Matcher (Para Arbitraje)

**Descripción**: Si la estrategia es de arbitraje, validar que la liquidez en la contraparte (Pinnacle/Bet365) también soporte el tamaño de la orden con el mismo ROI.

**Implementación**:
```python
def _check_hedge_liquidity_match(
    self, 
    polymarket_capacity: float,
    required_roi: float
) -> bool:
    """
    Verifica que la contraparte tenga liquidez suficiente.
    
    Args:
        polymarket_capacity: Capacidad calculada en Polymarket
        required_roi: ROI mínimo requerido
    
    Returns:
        True si la contraparte puede soportar el hedge
    """
    if not self.external_data:
        return False
    
    # Obtener liquidez de contraparte
    external_liquidity = self.external_data.get("available_liquidity", 0)
    external_price = self.external_data.get("price", 0)
    
    if external_liquidity == 0 or external_price == 0:
        return False
    
    # Calcular si la contraparte puede soportar el tamaño
    # Simplificado: verificar que haya liquidez suficiente
    return external_liquidity >= polymarket_capacity * 0.9  # 90% de margen
```

---

## Referencias

- `docs/BACKEND_ARCHITECTURE_STRATEGIES.md` - Arquitectura de estrategias
- `backend/app/core/strategy_engine/graph_runtime.py` - Runtime de grafos
- `backend/app/core/strategy_engine/nodes/` - Nodos existentes
- `backend/app/core/decision_trace/decision_trace_service.py` - Servicio de traces
- `frontend/hooks/useWebSocket.ts` - Hook de WebSocket
- `docs/PENDING/template_estrategy_live_control.html` - Template V3.1 (Profit Depth Edition)

---

**Última actualización**: 2025-12-21 (Añadidos indicadores de rentabilidad y fases 10-12)

