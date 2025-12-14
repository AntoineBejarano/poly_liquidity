"""
Dashboard API endpoint.
"""
from fastapi import APIRouter, Depends
from app.core.state import state
from app.api.auth import get_current_user
from app.api.auth import User
from app.core.execution.polymarket_client_wrapper import get_polymarket_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
):
    """Get dashboard data."""
    # Calculate realized PnL
    realized_pnl = 0.0
    # TODO: Calculate from resolved positions
    
    # Calculate unrealized PnL
    unrealized_pnl = 0.0
    for position_state in state.positions.values():
        if position_state.resolved:
            continue
        
        # Get current price from market
        market_state = state.markets.get(position_state.market_id)
        if market_state and market_state.last_price:
            cost_total = position_state.size * position_state.avg_price
            theoretical_value = position_state.size * market_state.last_price
            unrealized_pnl += theoretical_value - cost_total
    
    # Calculate global exposure
    global_exposure = 0.0
    for exposure_state in state.exposures.values():
        global_exposure += exposure_state.notional
    
    # Count active markets
    active_markets = len([m for m in state.markets.values() if m.last_price])
    
    # Get actual balance from Polymarket - CON CACHE para evitar exceder rate limits
    # El balance se cachea por 60 segundos para no hacer llamadas constantes a Polymarket
    # Límite de Polymarket: 125 requests / 10s para CLOB_BALANCE_ALLOWANCE_GET
    base_equity = 0.0
    try:
        from app.core.api_cache import api_cache
        from datetime import timedelta
        
        # Intentar obtener balance del cache primero
        cache_key = "polymarket_balance"
        cached_balance = await api_cache.get(cache_key)
        
        if cached_balance is not None:
            # Usar balance cacheado (válido por 60 segundos)
            base_equity = cached_balance
            logger.debug(f"Using cached balance: {base_equity}")
        else:
            # Cache expirado o no existe - obtener balance real de Polymarket
            polymarket_client = get_polymarket_client()
            is_avail = polymarket_client.is_available()
            
            if is_avail:
                balance = await polymarket_client.get_balance()
                
                if balance is not None:
                    base_equity = balance
                    # Cachear el balance por 60 segundos
                    await api_cache.set(cache_key, balance, ttl=timedelta(seconds=60))
                    logger.info(f"Got balance from Polymarket and cached: {base_equity}")
                else:
                    logger.warning("Could not get balance from Polymarket, returning None")
                    base_equity = None
            else:
                logger.warning("Polymarket client not available, returning None")
                base_equity = None
    except Exception as e:
        logger.error(f"Error getting balance from Polymarket: {e}", exc_info=True)
        base_equity = None
    
    # #region agent log
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"dashboard.py:73","message":"Final equity calculation","data":{"base_equity":base_equity,"realized_pnl":realized_pnl,"unrealized_pnl":unrealized_pnl,"equity":base_equity + realized_pnl + unrealized_pnl},"timestamp":int(time.time()*1000)})+"\n")
    # #endregion
    
    # Equity es solo el balance real de Polymarket (sin sumar PnL)
    # El usuario quiere ver el balance real, no un cálculo
    # Si no se pudo obtener el balance, retornar None en lugar de inventar un valor
    equity = base_equity if base_equity is not None else 0.0
    
    # #region agent log
    with open(r'c:\develop\repositorios\poly_liquidity\.cursor\debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"dashboard.py:100","message":"Final equity calculation","data":{"base_equity":base_equity,"equity":equity,"realized_pnl":realized_pnl,"unrealized_pnl":unrealized_pnl},"timestamp":int(time.time()*1000)})+"\n")
    # #endregion
    
    return {
        "equity": equity,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "global_exposure": global_exposure,
        "active_markets": active_markets,
        "system_active": state.system_active,
    }

