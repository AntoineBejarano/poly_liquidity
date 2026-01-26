"""
Metrics API endpoints.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.core.metrics.metrics_service import metrics_service
from app.core.latency_monitor import latency_monitor
from app.api.auth import get_current_user
from app.api.auth import User
import asyncio
import json
from datetime import datetime, timedelta

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


@router.get("/runtime")
async def get_runtime_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Get runtime metrics summary.
    
    Returns:
        - runtime_mode: Current runtime mode (GREEN/YELLOW/RED)
        - tick_duration_ms: Duration of main tick
        - execution_latency_ms: Execution latency
        - risk_exposure: Risk exposure metrics
        - checkers: Checker status
        - timestamp: Current timestamp
    """
    return metrics_service.get_current_metrics()


@router.get("/execution/p95_latency")
async def get_execution_latency_p95(
    current_user: User = Depends(get_current_user),
):
    """
    Get 95th percentile execution latency.
    
    Returns:
        - p95: 95th percentile latency in ms
        - p50: 50th percentile latency in ms
        - p99: 99th percentile latency in ms
    """
    stats = metrics_service.store.calculate_percentiles("execution_latency_ms")
    return {
        "p50": stats.get("p50", 0.0),
        "p95": stats.get("p95", 0.0),
        "p99": stats.get("p99", 0.0),
        "count": stats.get("count", 0)
    }


@router.get("/risk/exposure")
async def get_risk_exposure(
    current_user: User = Depends(get_current_user),
):
    """
    Get risk exposure metrics.
    
    Returns:
        - total: Total exposure
        - by_market: Exposure per market
    """
    latest = metrics_service.store.get_latest_metric("risk_exposure_total")
    total = latest["value"] if latest else 0.0
    
    # Get exposure per market
    history = metrics_service.store.get_metric_history(
        "risk_exposure_per_market",
        limit=100
    )
    
    by_market = {}
    for metric in history:
        market_id = metric.get("labels", {}).get("market_id")
        if market_id:
            by_market[market_id] = metric["value"]
    
    return {
        "total": total,
        "by_market": by_market,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/checkers/status")
async def get_checkers_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get checker status metrics.
    
    Returns:
        - checkers: Dict with checker status (latency, errors)
    """
    # Get latest metrics for each checker
    history = metrics_service.store.get_metric_history("checker_latency_ms", limit=100)
    
    checkers = {}
    for metric in history:
        checker_id = metric.get("labels", {}).get("checker")
        if checker_id:
            if checker_id not in checkers:
                checkers[checker_id] = {}
            checkers[checker_id]["latency_p95"] = metric["value"]
    
    # Get error counts
    error_history = metrics_service.store.get_metric_history("checker_errors", limit=100)
    for metric in error_history:
        checker_id = metric.get("labels", {}).get("checker")
        if checker_id:
            if checker_id not in checkers:
                checkers[checker_id] = {}
            checkers[checker_id]["error_count"] = int(metric["value"])
    
    return {
        "checkers": checkers,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/system/health")
async def get_system_health(
    current_user: User = Depends(get_current_user),
):
    """
    Get overall system health metrics.
    
    Returns:
        - runtime_mode: Current runtime mode
        - tick_duration_ms: Tick duration percentiles
        - execution_latency_ms: Execution latency percentiles
        - risk_exposure: Risk exposure
        - checkers: Checker status
        - timestamp: Current timestamp
    """
    metrics_data = metrics_service.get_current_metrics()
    
    # Add percentiles
    tick_stats = metrics_service.store.calculate_percentiles("tick_duration_ms")
    exec_stats = metrics_service.store.calculate_percentiles("execution_latency_ms")
    
    return {
        "runtime_mode": metrics_data.get("runtime_mode", "GREEN"),
        "tick_duration_ms": {
            "p50": tick_stats.get("p50", 0.0),
            "p95": tick_stats.get("p95", 0.0),
            "p99": tick_stats.get("p99", 0.0)
        },
        "execution_latency_ms": {
            "p50": exec_stats.get("p50", 0.0),
            "p95": exec_stats.get("p95", 0.0),
            "p99": exec_stats.get("p99", 0.0)
        },
        "risk_exposure": metrics_data.get("risk_exposure_total", {}),
        "checkers": metrics_data.get("checkers", {}),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stream")
async def stream_metrics(
    token: str = Query(..., description="Authentication token"),
    current_user: User = Depends(get_current_user),
):
    """
    Stream metrics in real-time using Server-Sent Events (SSE).
    
    Sends metrics updates every 1-2 seconds.
    """
    async def event_generator():
        while True:
            try:
                # Get current metrics
                metrics_data = metrics_service.get_current_metrics()
                
                # Format for streaming
                stream_data = {
                    "type": "metrics_update",
                    "latency_mode": metrics_data.get("runtime_mode", "GREEN"),
                    "tick_ms": metrics_data.get("tick_duration_ms", {}).get("value", 0),
                    "watchers": metrics_data.get("watchers_active", {}).get("value", 0),
                    "exposure_total": metrics_data.get("risk_exposure_total", {}).get("value", 0),
                    "runtime_mode": metrics_data.get("runtime_mode", "GREEN"),
                    "execution_latency_p95": metrics_data.get("execution_latency_ms_percentiles", {}).get("p95", 0),
                    "checker_errors": 0,  # TODO: Calculate from metrics
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Send update
                yield f"data: {json.dumps(stream_data)}\n\n"
                
                # Wait 2 seconds
                await asyncio.sleep(2.0)
            except Exception as e:
                print(f"ERROR: Error in metrics stream: {e}")
                await asyncio.sleep(2.0)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/prometheus")
async def get_prometheus_metrics(
    current_user: User = Depends(get_current_user),
):
    """
    Export metrics in Prometheus format.
    
    This endpoint can be scraped by Prometheus for integration with Grafana.
    """
    prometheus_text = metrics_service.prometheus_exporter.export_metrics()
    return prometheus_text
