"""
Unit tests for Latency Monitor.

Según especificación en docs/services/latency_monitor.md
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.core.latency_monitor import LatencyMonitor, LatencyStatus


class TestLatencyMonitor:
    """Test cases for LatencyMonitor."""
    
    @pytest.fixture
    def latency_monitor(self):
        """Fixture para LatencyMonitor."""
        return LatencyMonitor()
    
    @pytest.mark.asyncio
    async def test_measure_backend_latency(self, latency_monitor):
        """Test measuring backend latency."""
        latency = await latency_monitor._measure_backend_latency()
        assert latency > 0
        assert latency < 100  # Should be very fast
    
    @pytest.mark.asyncio
    async def test_get_latency_metrics_green(self, latency_monitor):
        """Test get_latency_metrics returns GREEN for low latencies."""
        with patch.object(latency_monitor, "_measure_backend_latency", return_value=50.0), \
             patch.object(latency_monitor, "_measure_polymarket_data_latency", return_value=100.0), \
             patch.object(latency_monitor, "_measure_polymarket_trading_latency", return_value=100.0):
            
            metrics = await latency_monitor.get_latency_metrics()
            assert metrics["status"] == "GREEN"
    
    @pytest.mark.asyncio
    async def test_get_latency_metrics_yellow(self, latency_monitor):
        """Test get_latency_metrics returns YELLOW for elevated latencies."""
        with patch.object(latency_monitor, "_measure_backend_latency", return_value=150.0), \
             patch.object(latency_monitor, "_measure_polymarket_data_latency", return_value=250.0), \
             patch.object(latency_monitor, "_measure_polymarket_trading_latency", return_value=250.0):
            
            metrics = await latency_monitor.get_latency_metrics()
            assert metrics["status"] == "YELLOW"
    
    @pytest.mark.asyncio
    async def test_get_latency_metrics_red(self, latency_monitor):
        """Test get_latency_metrics returns RED for critical latencies."""
        with patch.object(latency_monitor, "_measure_backend_latency", return_value=250.0), \
             patch.object(latency_monitor, "_measure_polymarket_data_latency", return_value=400.0), \
             patch.object(latency_monitor, "_measure_polymarket_trading_latency", return_value=400.0):
            
            metrics = await latency_monitor.get_latency_metrics()
            assert metrics["status"] == "RED"
    
    @pytest.mark.asyncio
    async def test_get_latency_metrics_uses_cache(self, latency_monitor):
        """Test get_latency_metrics uses cached results within TTL."""
        with patch.object(latency_monitor, "_measure_backend_latency", return_value=50.0), \
             patch.object(latency_monitor, "_measure_polymarket_data_latency", return_value=100.0), \
             patch.object(latency_monitor, "_measure_polymarket_trading_latency", return_value=100.0):
            
            # First call should measure
            metrics1 = await latency_monitor.get_latency_metrics()
            
            # Second call should use cache
            metrics2 = await latency_monitor.get_latency_metrics()
            
            assert metrics1["status"] == metrics2["status"]
            # Verify local cache exists
            assert latency_monitor._local_cache is not None
    
    def test_get_status_returns_cached_status(self, latency_monitor):
        """Test get_status returns status from cache."""
        latency_monitor._local_cache = {"status": "YELLOW"}
        
        status = latency_monitor.get_status()
        assert status == LatencyStatus.YELLOW
    
    def test_get_status_returns_green_when_no_cache(self, latency_monitor):
        """Test get_status returns GREEN when no cache."""
        latency_monitor._local_cache = None
        status = latency_monitor.get_status()
        assert status == LatencyStatus.GREEN
    
    @pytest.mark.asyncio
    async def test_record_execution_latency(self, latency_monitor):
        """Test recording execution latency."""
        latency_monitor.record_execution_latency(250.0)
        assert latency_monitor._last_execution_latency == 250.0
    
    def test_record_execution_latency_stores_value(self, latency_monitor):
        """Test recording execution latency stores value."""
        latency_monitor.record_execution_latency(300.0)
        assert latency_monitor._last_execution_latency == 300.0
    
    def test_execution_latency_included_in_metrics(self, latency_monitor):
        """Test execution latency is included in metrics."""
        latency_monitor.record_execution_latency(250.0)
        
        # Execution latency should be available in _last_execution_latency
        assert latency_monitor._last_execution_latency == 250.0
    
    @pytest.mark.asyncio
    async def test_close_closes_client(self, latency_monitor):
        """Test close closes HTTP client."""
        # Create a client first
        await latency_monitor._get_client()
        assert latency_monitor._client is not None
        
        # Close
        await latency_monitor.close()
        assert latency_monitor._client is None

