"""
Script de prueba rápida para verificar la conexión Redis.

Ejecutar: python -m scripts.test_redis_connection
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.redis_client import redis_client
from app.settings import settings


async def test_redis():
    """Test Redis connection and basic operations."""
    print("=" * 60)
    print("Test de Conexión Redis")
    print("=" * 60)
    
    # Check configuration
    print(f"\n1. Configuración:")
    print(f"   REDIS_URL: {'✅ Configurado' if settings.redis_url else '❌ No configurado'}")
    print(f"   REST URL: {'✅ Configurado' if settings.upstash_redis_rest_url else '❌ No configurado'}")
    print(f"   Redis Enabled: {'✅' if redis_client._enabled else '❌'}")
    print(f"   Connection Type: {redis_client._connection_type or 'None'}")
    
    if not redis_client._enabled:
        print("\n⚠️  Redis no está habilitado. Verifica las variables de entorno.")
        return
    
    # Test basic operations
    print(f"\n2. Operaciones Básicas:")
    
    # Test SET
    test_key = "test:connection"
    test_value = "test_value_123"
    print(f"   SET {test_key} = {test_value}...")
    set_result = await redis_client.set(test_key, test_value, ttl_seconds=10)
    print(f"   Resultado: {'✅ OK' if set_result else '❌ FAIL'}")
    
    # Test GET
    print(f"   GET {test_key}...")
    get_result = await redis_client.get(test_key)
    print(f"   Resultado: {'✅ OK' if get_result == test_value else f'❌ FAIL (got: {get_result})'}")
    
    # Test EXISTS
    print(f"   EXISTS {test_key}...")
    exists_result = await redis_client.exists(test_key)
    print(f"   Resultado: {'✅ OK' if exists_result else '❌ FAIL'}")
    
    # Test TTL
    print(f"   TTL {test_key}...")
    ttl_result = await redis_client.ttl(test_key)
    print(f"   Resultado: {'✅ OK' if ttl_result and ttl_result > 0 else f'❌ FAIL (got: {ttl_result})'}")
    
    # Test SET_NX (lock)
    lock_key = "test:lock"
    print(f"   SET_NX {lock_key} (lock test)...")
    lock_result = await redis_client.set_nx(lock_key, "locked", ttl_seconds=5)
    print(f"   Resultado: {'✅ OK (lock adquirido)' if lock_result else '❌ FAIL'}")
    
    # Test SET_NX again (should fail)
    print(f"   SET_NX {lock_key} (intento duplicado)...")
    lock_result2 = await redis_client.set_nx(lock_key, "locked2", ttl_seconds=5)
    print(f"   Resultado: {'✅ OK (lock no adquirido, como esperado)' if not lock_result2 else '❌ FAIL (debería fallar)'}")
    
    # Test JSON operations
    print(f"\n3. Operaciones JSON:")
    json_key = "test:json"
    json_value = {"test": "data", "number": 123}
    print(f"   SET_JSON {json_key}...")
    set_json_result = await redis_client.set_json(json_key, json_value, ttl_seconds=10)
    print(f"   Resultado: {'✅ OK' if set_json_result else '❌ FAIL'}")
    
    print(f"   GET_JSON {json_key}...")
    get_json_result = await redis_client.get_json(json_key)
    print(f"   Resultado: {'✅ OK' if get_json_result == json_value else f'❌ FAIL (got: {get_json_result})'}")
    
    # Cleanup
    print(f"\n4. Limpieza:")
    await redis_client.delete(test_key)
    await redis_client.delete(lock_key)
    await redis_client.delete(json_key)
    print("   ✅ Claves de prueba eliminadas")
    
    # Close connection
    await redis_client.close()
    print("\n" + "=" * 60)
    print("✅ Test completado exitosamente")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_redis())

