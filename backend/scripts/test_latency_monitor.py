"""
Script de prueba rápida para verificar LatencyMonitor con Redis.

Ejecutar: python -m scripts.test_latency_monitor
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.latency_monitor import latency_monitor


async def test_latency_monitor():
    """Test LatencyMonitor with Redis caching."""
    print("=" * 60)
    print("Test de LatencyMonitor con Redis")
    print("=" * 60)
    
    print("\n1. Primera llamada (debe medir latencias):")
    result1 = await latency_monitor.get_latency_metrics()
    print(f"   Timestamp: {result1.get('timestamp')}")
    print(f"   Cache Age: {result1.get('cache_age_seconds', 0)}s")
    print(f"   Backend Latency: {result1.get('backend_latency_ms')}ms")
    print(f"   Status: {result1.get('status')}")
    
    print("\n2. Segunda llamada (debe usar cache):")
    result2 = await latency_monitor.get_latency_metrics()
    print(f"   Timestamp: {result2.get('timestamp')}")
    print(f"   Cache Age: {result2.get('cache_age_seconds', 0)}s")
    print(f"   Backend Latency: {result2.get('backend_latency_ms')}ms")
    print(f"   Status: {result2.get('status')}")
    
    # Check if cache is working
    same_timestamp = result1.get('timestamp') == result2.get('timestamp')
    cache_age = result2.get('cache_age_seconds', 0)
    
    print(f"\n3. Verificación de Cache:")
    print(f"   Mismo timestamp: {'✅ OK' if same_timestamp else '❌ FAIL'}")
    print(f"   Cache age: {cache_age}s {'✅ OK (< 30s)' if cache_age < 30 else '⚠️  Stale'}")
    
    print("\n4. Force refresh:")
    result3 = await latency_monitor.get_latency_metrics(force_refresh=True)
    print(f"   Timestamp: {result3.get('timestamp')}")
    print(f"   Cache Age: {result3.get('cache_age_seconds', 0)}s")
    print(f"   Nuevo timestamp: {'✅ OK' if result3.get('timestamp') != result2.get('timestamp') else '❌ FAIL'}")
    
    # Close
    await latency_monitor.close()
    
    print("\n" + "=" * 60)
    print("✅ Test completado")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_latency_monitor())

