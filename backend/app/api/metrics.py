"""
Metrics API endpoints.
"""
from fastapi import APIRouter, Depends, Query
from app.core.latency_monitor import latency_monitor
from app.api.auth import get_current_user
from app.api.auth import User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/latency")
async def get_latency_metrics(
    force_refresh: bool = Query(False, description="Force refresh metrics bypassing cache"),
    current_user: User = Depends(get_current_user),
):
    """
    Get latency metrics for backend and Polymarket APIs.
    
    Returns:
        - backend_latency_ms: Internal backend processing latency
        - polymarket_data_latency_ms: Latency to Polymarket Data API
        - polymarket_trading_latency_ms: Latency to Polymarket Trading API (CLOB)
        - execution_latency_ms: End-to-end execution latency (order generation → confirmation)
        - status: Overall status (GREEN/YELLOW/RED)
    
    Status meanings:
        - GREEN: All latencies within acceptable range, full aggression allowed
        - YELLOW: Some latencies elevated, reduce size and aggression
        - RED: Critical latencies, stop new entries
    """
    metrics = await latency_monitor.get_latency_metrics(force_refresh=force_refresh)
    return metrics


