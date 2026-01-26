"""
Features calculator - Calcula métricas derivadas del orderbook.

⚠️ IMPORTANTE: Todas las funciones depth/impact/concentration son BUY-side only (asks).
Si un día operas SELL/NO, necesitarás funciones _sell() separadas con bids.
"""
import logging
from typing import List
from .models import OrderbookLevel

logger = logging.getLogger(__name__)


def compute_spread_bps(best_bid: float, best_ask: float) -> float:
    """
    Calcula spread en basis points.
    
    Args:
        best_bid: Mejor bid price
        best_ask: Mejor ask price
    
    Returns:
        Spread en basis points
    """
    if best_bid <= 0:
        return 0.0
    return ((best_ask - best_bid) / best_bid) * 10000


def compute_mid(best_bid: float, best_ask: float) -> float:
    """
    Calcula mid price.
    
    Args:
        best_bid: Mejor bid price
        best_ask: Mejor ask price
    
    Returns:
        Mid price
    """
    return (best_bid + best_ask) / 2.0


def compute_depth_usdc_at_bps_buy(
    asks: List[OrderbookLevel],
    best_ask_price: float,
    bps: int
) -> float:
    """
    Calcula depth en USDC a X bps del mejor ask (BUY side only).
    
    ⚠️ WARNING: Esta función es BUY-side only (asks).
    Para Near-Resolution (típicamente BUY YES), esto es correcto.
    Si un día operas SELL/NO, necesitarás una función _sell() separada.
    
    Args:
        asks: Lista de asks (asc price)
        best_ask_price: Mejor ask price (referencia)
        bps: Basis points desde best_ask
    
    Returns:
        Depth en USDC (suma de size * price para asks dentro del límite)
    """
    if not asks or best_ask_price <= 0:
        return 0.0
    
    # Límite de precio: best_ask * (1 + bps/10000)
    price_limit = best_ask_price * (1 + bps / 10000.0)
    
    depth_usdc = 0.0
    for level in asks:
        if level.price <= price_limit:
            depth_usdc += level.size * level.price
        else:
            break  # Asks están ordenados asc, podemos parar
    
    return depth_usdc


def compute_impact_bps_for_usdc_buy(
    asks: List[OrderbookLevel],
    best_ask_price: float,
    target_usdc: float
) -> float:
    """
    Calcula impacto en precio (bps) al ejecutar B USDC (BUY side only).
    
    ⚠️ WARNING: Esta función es BUY-side only (asks).
    Simula barrido de asks hasta gastar B USDC.
    
    Args:
        asks: Lista de asks (asc price)
        best_ask_price: Mejor ask price (referencia)
        target_usdc: Tamaño objetivo en USDC
    
    Returns:
        Impacto en basis points. Si no hay suficiente depth, retorna 1e9 (inf).
    """
    if not asks or best_ask_price <= 0 or target_usdc <= 0:
        return 0.0
    
    total_usdc_spent = 0.0
    total_shares_filled = 0.0
    
    for level in asks:
        if total_usdc_spent >= target_usdc:
            break
        
        # Skip niveles con price <= 0 (inválidos)
        if level.price <= 0:
            continue
        
        # Cuánto podemos gastar en este nivel
        remaining_usdc = target_usdc - total_usdc_spent
        usdc_at_this_level = min(remaining_usdc, level.size * level.price)
        shares_at_this_level = usdc_at_this_level / level.price
        
        total_usdc_spent += usdc_at_this_level
        total_shares_filled += shares_at_this_level
    
    # Si no hay suficiente depth, retornar inf
    if total_usdc_spent < target_usdc:
        return 1e9
    
    # Calcular precio promedio
    if total_shares_filled <= 0:
        return 0.0
    
    avg_price = total_usdc_spent / total_shares_filled
    
    # Impacto en basis points
    impact_bps = ((avg_price - best_ask_price) / best_ask_price) * 10000
    
    return impact_bps


def compute_concentration_top3_pct_buy(asks: List[OrderbookLevel]) -> float:
    """
    Calcula concentración de liquidez en top-3 levels (BUY side only).
    
    ⚠️ WARNING: Esta función es BUY-side only (asks).
    
    Args:
        asks: Lista de asks (asc price)
    
    Returns:
        Porcentaje de liquidez total en top-3 levels (0.0 - 1.0)
    """
    if not asks:
        return 0.0
    
    # Calcular total USDC en top-N
    total_usdc_topn = sum(level.size * level.price for level in asks)
    
    if total_usdc_topn <= 0:
        return 0.0
    
    # Calcular total USDC en top-3
    top3_asks = asks[:3]
    total_usdc_top3 = sum(level.size * level.price for level in top3_asks)
    
    # Ratio (clamp 0..1)
    ratio = total_usdc_top3 / total_usdc_topn
    return min(1.0, max(0.0, ratio))


def compute_update_rate_hz(update_timestamps: List[int], window_seconds: int = 10) -> float:
    """
    Calcula tasa de actualización (Hz) en ventana rolling.
    
    Args:
        update_timestamps: Lista de timestamps (ms) de updates
        window_seconds: Ventana de tiempo en segundos (default: 10s)
    
    Returns:
        Tasa de actualización en Hz (updates por segundo)
    """
    if not update_timestamps:
        return 0.0
    
    window_ms = window_seconds * 1000
    
    # Filtrar timestamps dentro de la ventana
    now_ms = update_timestamps[-1] if update_timestamps else 0
    cutoff_ms = now_ms - window_ms
    
    recent_updates = [ts for ts in update_timestamps if ts >= cutoff_ms]
    
    if len(recent_updates) < 2:
        return 0.0
    
    # Calcular Hz
    time_span_ms = recent_updates[-1] - recent_updates[0]
    if time_span_ms <= 0:
        return 0.0
    
    hz = (len(recent_updates) - 1) / (time_span_ms / 1000.0)
    return hz


def compute_replenishment_score(
    depth_history: List[float],
    baseline_depth: float
) -> float:
    """
    Calcula score de reposición de liquidez (heurística MVP).
    
    Cuando detectas que depth@50bps cae > X% y luego se recupera, sube score.
    Simplificado: score = EMA(Δdepth_positive / baseline_depth)
    
    Args:
        depth_history: Historial de depth@50bps (últimos N updates)
        baseline_depth: Depth baseline para normalización
    
    Returns:
        Score de reposición (0.0 - 1.0)
    """
    if not depth_history or baseline_depth <= 0:
        return 0.0
    
    # Simplificación MVP: usar último valor vs baseline
    current_depth = depth_history[-1] if depth_history else 0.0
    
    if current_depth <= 0:
        return 0.0
    
    # Ratio positivo de cambio
    delta_positive = max(0.0, current_depth - baseline_depth)
    score = delta_positive / baseline_depth
    
    # Clamp 0..1
    return min(1.0, max(0.0, score))

